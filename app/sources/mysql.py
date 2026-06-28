"""MySQL source."""

from sqlalchemy import text

from .base import Source


class MySQLSource(Source):
    """Reflect a live MySQL database.

    Uses default table reflection from the base class. For views, MySQL's
    information_schema exposes the full SELECT definition, which we wrap into a
    portable ``CREATE VIEW`` statement. Expects a URL like::

        mysql+pymysql://user:pass@host/db
    """

    name = "mysql"

    def reflect_views(self, engine):
        """Return [(view_name, create_view_sql), ...] from information_schema."""
        sql = text(
            "SELECT TABLE_NAME, VIEW_DEFINITION "
            "FROM information_schema.VIEWS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "ORDER BY TABLE_NAME"
        )
        views = []
        with engine.connect() as conn:
            for name, definition in conn.execute(sql):
                if definition:
                    views.append((name, f"CREATE VIEW {name} AS {definition}"))
        return views
