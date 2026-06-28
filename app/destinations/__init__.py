"""Destination registry.

A destination knows how to turn reflected MetaData into target-specific
schema/data SQL and how to push that SQL to a live target. Register new
destinations in DESTINATIONS.
"""

from .base import Destination
from .mssql import MSSQLDestination

DESTINATIONS = {
    MSSQLDestination.name: MSSQLDestination(),
}

__all__ = ["Destination", "DESTINATIONS"]
