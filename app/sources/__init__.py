"""Source registry.

A source knows how to connect to a live database and reflect its structure
into a SQLAlchemy MetaData object. Register new sources in SOURCES.
"""

from .base import Source
from .mysql import MySQLSource

SOURCES = {
    MySQLSource.name: MySQLSource(),
}

__all__ = ["Source", "SOURCES"]
