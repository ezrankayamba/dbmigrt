"""Base class for migration sources."""

from sqlalchemy import create_engine, MetaData, inspect, text


class Source:
    """A migration source: connect to a live DB and reflect its schema."""

    name = ""

    def reflect(self, url):
        """Return (engine, metadata) for the database at ``url``."""
        engine = create_engine(url)
        md = MetaData()
        md.reflect(bind=engine)
        return engine, md

    def reflect_views(self, engine):
        """Return [(view_name, select_sql), ...] for the source database.

        Default implementation uses SQLAlchemy's inspector, which exposes view
        names and their definitions on engines that support it. The returned
        SQL is the source dialect's SELECT body; destinations are responsible
        for any translation. Subclasses may override for dialect-specific
        definition retrieval.
        """
        insp = inspect(engine)
        try:
            names = insp.get_view_names()
        except NotImplementedError:
            return []
        views = []
        for name in names:
            try:
                definition = insp.get_view_definition(name)
            except NotImplementedError:
                definition = None
            if definition:
                views.append((name, definition))
        return views
