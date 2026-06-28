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
pip install pyinstaller
pyinstaller --onefile --name dbmigrt app/__main__.py
# -> dist/dbmigrt  (Linux/macOS)  or  dist\dbmigrt.exe  (Windows)
```

Build on the OS you'll run it on. Direct `push` needs the Microsoft ODBC driver;
`--client` mode needs only `sqlcmd`.

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
