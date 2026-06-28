# CLAUDE.md

Guidance for Claude (and humans) working in this repository.

## What this is

`dbmigrt` is a pluggable database migrator. It reflects a live **source**
database (no application code required), generates **destination**-compatible
`schema.sql`, `data.sql`, and (when present) `views.sql`, and optionally pushes
them to the target.

Today it supports **MySQL → SQL Server**. The architecture is built so other
engines slot in without touching the CLI.

## Architecture (read before editing)

For the complete design rationale, requirements, and traceability, see
[`docs/SDD.md`](docs/SDD.md).

The design separates three concerns: reflecting a source, generating target
SQL, and the CLI that wires them. Engines are looked up from registries.

```
app/
  cli.py                 Thin Click CLI. Resolves source+dest from registries.
  ordering.py            FK-dependency table ordering (shared).
  sources/
    base.py              Source base class: reflect(url) -> (engine, metadata)
    mysql.py             MySQLSource
    __init__.py          SOURCES registry {name: instance}
  destinations/
    base.py              Destination base: write_schema / write_data /
                         write_views / push_direct / push_client
    mssql.py             MSSQLDestination (identity, FK toggling, batching)
    __init__.py          DESTINATIONS registry {name: instance}
```

Data flow:

```
export:  source.reflect(url) -> (engine, metadata)
         dest.write_schema(metadata) -> schema.sql
         dest.write_data(engine, metadata) -> data.sql
         source.reflect_views(engine) -> dest.write_views() -> views.sql (if any)
push:    dest.push_direct(url, files)   OR   dest.push_client(files, ...)
         files = [schema.sql, data.sql, views.sql?]  (views applied last)
```

## Hard invariants — do not regress these

These are the correctness guarantees of the MSSQL destination. Any change must
preserve them (the tests in `tests/` check several):

1. **Primary keys preserved.** `SET IDENTITY_INSERT` + inlined literal values
   keep original `Id`s, so foreign-key references remain valid. Only applied to
   tables with a single auto-increment integer PK.
2. **FK-safe load.** All FK constraints are disabled before data load and
   re-validated (`WITH CHECK CHECK CONSTRAINT ALL`) after. Table order must
   still be parent-first where possible (`ordering.ordered_tables`).
3. **Batch limit.** Multi-row `VALUES` inserts never exceed 1000 rows (T-SQL
   cap). See `BATCH` in `destinations/mssql.py`.
4. **GO batching.** `push` splits scripts on lines containing only `GO`.
5. **Apply order.** Files are pushed schema → data → views. Views are written
   to a separate `views.sql` and applied last because they may depend on both
   tables and loaded data. `views.sql` is optional (skipped when the source has
   no views).

## Conventions

- CLI stays thin. No engine-specific logic in `cli.py`; it only resolves
  registries and delegates.
- `--from`/`--to` choices are generated from registry keys. Never hardcode
  engine names in the CLI.
- Schema and data are always separate files.
- Keep prose/comments explaining *why*, not *what*.

## How to extend (common task)

Add a **source**: subclass `Source`, implement `reflect` if defaults don't fit,
register in `SOURCES`. See `sources/CLAUDE.md`.

Add a **destination**: subclass `Destination`, implement `write_schema`,
`write_data`, `write_views`, `push_direct`, `push_client`, register in
`DESTINATIONS`. See `destinations/CLAUDE.md`.

No CLI changes are needed for either.

## Dev commands

```bash
pip install -e ".[dev,mssql]"     # editable install with test + driver deps
python -m pytest -q               # run tests (uses SQLite as a source stand-in)
python -m app --help              # run the CLI
python docs/build_pdf.py          # regenerate docs/SDD.pdf from SDD.md
pyinstaller --onefile --name dbmigrt app/__main__.py   # single binary
```

## Testing notes

Tests use **SQLite** as a stand-in source so CI needs no live MySQL/MSSQL. The
same SQLAlchemy reflection path is exercised, so ordering, identity detection,
FK wrapping, and batching are all covered. When adding a destination, add a test
that asserts its invariants the same way `tests/test_export_sqlite.py` does.

## Known limitations (intentional, document don't "fix" silently)

- Type translation for unsigned ints, `JSON`, and `TEXT`/`BLOB` may need manual
  review in `schema.sql`. This is inherent to MySQL→MSSQL.
- `push_direct` to MSSQL requires the Microsoft ODBC driver; `push_client`
  needs only `sqlcmd`.
