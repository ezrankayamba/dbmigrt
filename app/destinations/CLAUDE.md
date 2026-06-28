# CLAUDE.md — destinations

A **destination** turns reflected `MetaData` (and reflected views) into
target-specific SQL and applies it. It owns all dialect-specific behaviour.

## The five methods

```python
write_schema(path, md)              # CREATE TABLE / index DDL -> path
write_data(path, engine, md)        # INSERTs (+ any wrapping) -> path
write_views(path, views)            # CREATE VIEW from [(name, select_sql), ...] -> path
push_direct(url, files)             # apply files via a DB driver
push_client(files, server, db, extra)  # apply files via a client binary
```

Schema, data, and views are always separate files. `views` is the list of
`(name, select_sql)` pairs returned by `Source.reflect_views`; the SELECT body
is in the *source* dialect, so `write_views` owns any translation.

## Adding a destination

1. Create `destinations/<engine>.py`, subclass `Destination`, set `name` and
   `dialect`, implement the five methods. Reuse `ordering.ordered_tables(md)`
   for parent-first ordering.

2. Register in `destinations/__init__.py`:

   ```python
   from .postgres import PostgresDestination
   DESTINATIONS = {
       MSSQLDestination.name: MSSQLDestination(),
       PostgresDestination.name: PostgresDestination(),
   }
   ```

## Invariants a destination should uphold

If the target enforces FKs and uses auto-increment keys, preserve these (the
MSSQL implementation is the reference):

- **Preserve primary keys** so FK references survive (MSSQL uses
  `SET IDENTITY_INSERT`; Postgres would use explicit column lists and a
  sequence resync via `setval`).
- **Make the load FK-safe** — disable/defer constraints during load, re-validate
  after, and still order tables parent-first where possible.
- **Respect the dialect's multi-row INSERT limit** (MSSQL: 1000 rows/statement).
- **Batch separator** — MSSQL uses `GO`; other targets may not. If your push
  reads the generated files, split on the separator your `write_*` emitted.
- **Apply views last** — `push` orders files schema → data → views, since views
  may reference both tables and loaded data. `views.sql` is optional (skipped
  when the source has none).

## Why these are invariants

A migration that renumbers primary keys silently breaks every foreign-key
relationship in the data. Disabling FK checks during load avoids ordering
deadlocks (self-referential and circular FKs) that can't be solved by table
order alone. Re-validating afterwards surfaces genuinely orphaned rows instead
of hiding them.
