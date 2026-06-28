# CLAUDE.md — sources

A **source** connects to a live database and reflects its structure into a
SQLAlchemy `MetaData` object. That's the only contract.

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
- The returned `engine` must stay usable for streaming row reads during
  `write_data` (the destination calls `engine.connect()` with
  `stream_results=True`).
- Do not do any destination-specific work here. Sources are
  destination-agnostic.
