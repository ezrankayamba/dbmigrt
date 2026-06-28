# CLAUDE.md — sources

A **source** connects to a live database and reflects its structure into a
SQLAlchemy `MetaData` object, and optionally reflects its views. That's the
only contract.

## Adding a source

1. Create `sources/<engine>.py`:

   ```python
   from .base import Source

   class PostgresSource(Source):
       name = "postgres"
       # Override reflect() only if default reflection needs adjusting,
       # e.g. selecting a specific schema:
       #
       # def reflect(self, url):
       #     engine = create_engine(url)
       #     md = MetaData(schema="public")
       #     md.reflect(bind=engine)
       #     return engine, md
   ```

2. Register it in `sources/__init__.py`:

   ```python
   from .postgres import PostgresSource
   SOURCES = {
       MySQLSource.name: MySQLSource(),
       PostgresSource.name: PostgresSource(),
   }
   ```

That's it — the CLI's `--from` choices update automatically.

## Contract

- `reflect(url) -> (engine, metadata)`.
- `reflect_views(engine) -> [(view_name, select_sql), ...]`. The base
  implementation uses SQLAlchemy's inspector and returns `[]` when the dialect
  doesn't support view reflection. The returned SQL is the *source* dialect's
  SELECT body — translation is the destination's job. Override only for
  dialect-specific definition retrieval.
- The returned `engine` must stay usable for streaming row reads during
  `write_data` (the destination calls `engine.connect()` with
  `stream_results=True`).
- Do not do any destination-specific work here. Sources are
  destination-agnostic.
