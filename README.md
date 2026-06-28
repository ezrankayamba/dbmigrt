# dbmigrt

A pluggable database migrator. Reflects a live **source** database (no app code
needed), generates **destination**-compatible `schema.sql` and `data.sql`, and
optionally pushes them to the target.

| role        | engine |
|-------------|--------|
| source      | mysql  |
| destination | mssql  |

More engines can be added without touching the CLI — see `CLAUDE.md`.

## Install

```bash
pip install -e .                 # from source
# or with the direct-push driver and dev tools:
pip install -e ".[mssql,dev]"
```

## Build a single binary

```bash
pip install ".[mssql]" pyinstaller
pyinstaller --onefile --name dbmigrt \
  --collect-submodules sqlalchemy.dialects \
  --hidden-import pymysql --hidden-import pyodbc \
  app/__main__.py
# -> dist/dbmigrt  (Linux/macOS)  or  dist\dbmigrt.exe  (Windows)
```

The `--collect-submodules`/`--hidden-import` flags are required: SQLAlchemy
loads driver dialects by name at connect time, so PyInstaller can't see them
statically and the binary would fail to reach the database without them.

Build on the OS you'll run it on. Tagging a release (`vX.Y.Z`) builds these
binaries for Linux/macOS/Windows via CI — see `.github/workflows/release.yml`.
Direct `push` needs the Microsoft ODBC driver; `--client` mode needs only
`sqlcmd`.

## Use

Export where MySQL is reachable:

```bash
dbmigrt export --url "mysql+pymysql://user:pass@mysqlhost/db" --out ./out
```

Push where SQL Server is reachable — pick ONE mode:

```bash
# direct connect (needs ODBC driver)
dbmigrt push --in ./out \
  --url "mssql+pyodbc://user:pass@host/db?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"

# via sqlcmd (no driver); args after `--` pass through to sqlcmd
dbmigrt push --in ./out --client -S localhost -d mydb -- -U sa -P 'secret'
```

`--from`/`--to` default to `mysql`/`mssql` and can be omitted for now. If the two
machines can't reach each other, copy the `out/` folder between them.

## Troubleshooting

**Passwords with special characters must be percent-encoded in `--url`.** The
URL is parsed as a URL, so a raw `@`, `:`, `/`, `?`, `#`, or space in the
password misparses silently — e.g. `...://app:p@ss@host/db` reads the password
as `p` and the host as `ss@host`. Encode it:

```bash
python -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" 'p@ss:w0/rd'
# -> p%40ss%3Aw0%2Frd     then:  mysql+pymysql://app:p%40ss%3Aw0%2Frd@host/db
```

(`@`→`%40`, `:`→`%3A`, `/`→`%2F`, `?`→`%3F`, `#`→`%23`, space→`%20`, `%`→`%25`.)
The `push --client` mode takes the password as a real argument (`-- -U sa -P
'p@ss'`), so it does **not** need encoding.

**Stuck at `Reflecting mysql at ...`?** That's the connect step blocking on an
unreachable host/port — usually a misparsed URL (see above), wrong host/port,
or a firewall. The MySQL source uses a 10s connect timeout so it errors instead
of hanging; tune it with `?connect_timeout=N` in the URL. Verify connectivity
directly with `nc -vz <host> 3306`.

## Guarantees

- Id / primary-key values preserved exactly (IDENTITY_INSERT + inlined values).
- FK constraints disabled during load, re-validated after — order-independent.
- Views exported to a separate `views.sql`; push order is schema → data → views.
- Schema applied before data; scripts split on `GO` batches.
- Spot-check `schema.sql` for unsigned ints, JSON, TEXT/BLOB.

## Project layout

```
app/
  cli.py            thin Click CLI
  ordering.py       FK-dependency table ordering
  sources/          source registry (mysql)
  destinations/     destination registry (mssql)
tests/              pytest suite (SQLite stand-in source)
```

## Development

```bash
python -m pytest -q
python -m dbmigrt --help
```

See [`docs/SDD.pdf`](docs/SDD.pdf) (source: [`docs/SDD.md`](docs/SDD.md)) for the full design document, and `CLAUDE.md` for architecture and how to add engines.
