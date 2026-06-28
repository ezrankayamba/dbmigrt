"""Base class for migration destinations."""


class Destination:
    """A migration destination: generate target SQL and push it.

    Subclasses implement the methods below. Schema, views, and data are written
    as separate files so they can be reviewed, edited, and applied
    independently and in the correct order (schema -> data -> views).
    """

    name = ""
    dialect = None

    def write_schema(self, path, md):
        """Write CREATE TABLE / index DDL for all tables to ``path``."""
        raise NotImplementedError

    def write_data(self, path, engine, md):
        """Write INSERT statements for all table data to ``path``."""
        raise NotImplementedError

    def write_views(self, path, views):
        """Write CREATE VIEW statements to ``path``.

        ``views`` is a list of (name, create_sql) pairs as returned by
        ``Source.reflect_views``. Returns the number of views written.
        """
        raise NotImplementedError

    def push_direct(self, url, files):
        """Apply ``files`` by connecting to ``url`` via a driver."""
        raise NotImplementedError

    def push_client(self, files, server, database, extra):
        """Apply ``files`` by shelling out to the target's client binary."""
        raise NotImplementedError
