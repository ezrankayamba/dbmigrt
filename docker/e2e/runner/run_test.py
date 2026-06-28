#!/usr/bin/env python3
"""End-to-end MySQL -> SQL Server (Azure SQL Edge) migration test.

Runs the real dbmigrt CLI: export against live MySQL, push against live
SQL Edge, then verifies row counts, identity preservation, FK integrity,
and the migrated view. Designed to surface translation gaps the SQLite
stand-in test cannot.
"""
import os
import subprocess
import sys
import time

import pymysql
import pymssql

MYSQL = dict(host="mysql", port=3306, user="root", password="root", database="testdb")
MSSQL = dict(server="mssql", port=1433, user="sa", password="Passw0rd!2024")
OUT = "/out"
DESTDB = "destdb"


def log(msg):
    print(f"\n=== {msg} ===", flush=True)


def wait_for(name, fn, tries=60, delay=3):
    for i in range(tries):
        try:
            fn()
            print(f"  {name} ready", flush=True)
            return
        except Exception as e:
            if i % 5 == 0:
                print(f"  waiting for {name}... ({type(e).__name__})", flush=True)
            time.sleep(delay)
    raise SystemExit(f"!! {name} never became ready")


def mssql_conn(database=None, autocommit=True):
    return pymssql.connect(
        server=MSSQL["server"], port=str(MSSQL["port"]),
        user=MSSQL["user"], password=MSSQL["password"],
        database=database or "master", autocommit=autocommit,
    )


def run_cli(args):
    print(f"  $ python -m app {' '.join(args)}", flush=True)
    r = subprocess.run(
        [sys.executable, "-m", "app", *args],
        cwd="/work", capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": "/work"},
    )
    print(r.stdout, flush=True)
    if r.stderr:
        print("  [stderr]\n" + r.stderr, flush=True)
    return r


def main():
    log("Wait for databases")
    wait_for("mysql", lambda: pymysql.connect(**MYSQL).close())
    wait_for("mssql", lambda: mssql_conn().close())

    log("Create destination database")
    with mssql_conn() as c:
        cur = c.cursor()
        cur.execute(
            f"IF DB_ID('{DESTDB}') IS NULL CREATE DATABASE [{DESTDB}]")
    print(f"  {DESTDB} ready", flush=True)

    log("EXPORT (mysql -> sql files)")
    url = f"mysql+pymysql://{MYSQL['user']}:{MYSQL['password']}@{MYSQL['host']}:{MYSQL['port']}/{MYSQL['database']}"
    r = run_cli(["export", "--url", url, "--out", OUT])
    if r.returncode != 0:
        raise SystemExit("!! export failed")

    log("Generated schema.sql")
    print(open(f"{OUT}/schema.sql").read(), flush=True)
    log("Generated views.sql")
    try:
        print(open(f"{OUT}/views.sql").read(), flush=True)
    except FileNotFoundError:
        print("  (no views.sql)", flush=True)

    log("PUSH (sql files -> sql edge)")
    push_url = (f"mssql+pymssql://{MSSQL['user']}:{MSSQL['password']}"
                f"@{MSSQL['server']}:{MSSQL['port']}/{DESTDB}")
    r = run_cli(["push", "--in", OUT, "--url", push_url])
    push_ok = r.returncode == 0
    if not push_ok:
        print("!! push failed — see error above", flush=True)

    log("VERIFY")
    verify(push_ok)


def verify(push_ok):
    # source counts
    src = {}
    with pymysql.connect(**MYSQL) as c:
        cur = c.cursor()
        for t in ("parent", "child", "employee", "tag"):
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            src[t] = cur.fetchone()[0]
    print(f"  source counts:      {src}", flush=True)

    if not push_ok:
        print("  destination not populated (push failed); "
              "skipping count comparison", flush=True)
        return False

    dst = {}
    ok = True
    with mssql_conn(database=DESTDB) as c:
        cur = c.cursor()
        for t in src:
            cur.execute(f"SELECT COUNT(*) FROM [{t}]")
            dst[t] = cur.fetchone()[0]
        print(f"  destination counts: {dst}", flush=True)
        for t in src:
            if src[t] != dst[t]:
                print(f"  !! count mismatch on {t}: {src[t]} != {dst[t]}", flush=True)
                ok = False

        # identity preserved
        cur.execute("SELECT id, name FROM [parent] ORDER BY id")
        rows = cur.fetchall()
        print(f"  parent rows: {rows}", flush=True)
        if [r[0] for r in rows] != [1, 2, 3]:
            print("  !! parent ids not preserved", flush=True); ok = False

        # view migrated
        try:
            cur.execute("SELECT COUNT(*) FROM [v_active_children]")
            print(f"  v_active_children rows: {cur.fetchone()[0]}", flush=True)
        except Exception as e:
            print(f"  !! view query failed: {e}", flush=True); ok = False

        # FK integrity actually enforced post-load
        try:
            cur.execute("INSERT INTO [child] (parent_id) VALUES (9999)")
            print("  !! FK NOT enforced (orphan insert succeeded)", flush=True); ok = False
        except Exception:
            print("  FK enforced (orphan insert rejected) ✓", flush=True)

    print(f"\n  RESULT: {'PASS' if ok else 'FAIL'}", flush=True)
    return ok


if __name__ == "__main__":
    main()
