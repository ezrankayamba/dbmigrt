# End-to-end migration test (Docker)

Exercises a real **MySQL → SQL Server** migration end to end, against live
engines, using the actual `dbmigrt` CLI. This catches dialect/translation
issues the SQLite-based unit suite (`tests/`) cannot — invalid type renders,
overflow, charset loss, view qualifiers.

It is **opt-in** and not part of `pytest`: it pulls ~1.5 GB of images and
starts two databases.

## Run

```bash
cd docker/e2e
docker compose up --build --abort-on-container-exit --exit-code-from runner
```

A passing run ends with:

```
=== VERIFY ===
  destination counts: {'parent': 3, 'child': 3, 'employee': 2, 'tag': 2}
  parent rows: [(1, 'Acme'), (2, "O'Brien & Co"), (3, 'Çağrı Ünicode')]
  v_active_children rows: 2
  FK enforced (orphan insert rejected) ✓
  RESULT: PASS
```

Tear down (containers + volumes):

```bash
docker compose down -v
```

## What it does

1. **mysql** (`mysql:8.0`) is seeded from [`mysql/init.sql`](mysql/init.sql)
   with a schema chosen to stress translation: FK + self-referential FK, a
   non-autoincrement PK, a view, and the MySQL-only types (`ENUM`, `JSON`,
   `INT/BIGINT UNSIGNED`, `TINYINT(1)`, `DOUBLE`, `TEXT`), plus rows with
   apostrophes, Unicode, and NULLs.
2. **mssql** is the migration target. We use **Azure SQL Edge**, the
   arm64-native SQL Server engine (same TDS/T-SQL). On amd64 you can switch the
   image to `mcr.microsoft.com/mssql/server`.
3. **runner** ([`runner/run_test.py`](runner/run_test.py)) waits for both DBs,
   creates the destination database, runs `dbmigrt export` then `dbmigrt push`
   (direct mode via `pymssql`), and verifies row counts, identity
   preservation, the migrated view, and post-load FK enforcement.

The runner mounts the repo at `/work`, so it always runs the **working-tree**
code — edit `app/` and re-run without rebuilding the image.

## Notes

- `dbmigrt`'s own `push` transports need an ODBC driver (`push_direct`) or
  `sqlcmd` (`push_client`); the runner uses the `mssql+pymssql` driver purely to
  keep the image small and arm64-friendly. The generated SQL is identical.
- Credentials here are throwaway and for local testing only.
