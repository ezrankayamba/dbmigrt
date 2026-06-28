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

    # Fail fast on an unreachable host instead of blocking on TCP backoff.
    # Override per-run with ?connect_timeout=N in the URL.
    connect_args = {"connect_timeout": 10}

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
            db = conn.execute(text("SELECT DATABASE()")).scalar()
            prefix = f"`{db}`."  # how MySQL qualifies table refs in view bodies
            for name, definition in conn.execute(sql):
                if definition:
                    # MySQL fully-qualifies table references with the source
                    # schema (`db`.`tbl`). Strip that prefix so the view binds
                    # to the destination's default schema rather than a
                    # non-existent source-named one. Aliases (`c`.`col`) are
                    # single-part and unaffected.
                    definition = definition.replace(prefix, "")
                    views.append((name, f"CREATE VIEW {name} AS {definition}"))
        return views
