"""Table ordering shared across destinations."""

import sys

from sqlalchemy.exc import CircularDependencyError


def ordered_tables(md):
    """Return reflected tables in FK-dependency order (parents first).

    Falls back to alphabetical order when a circular foreign key makes a
    total order impossible. That's safe here because every destination
    disables FK enforcement during the data load.
    """
    try:
        return list(md.sorted_tables)
    except CircularDependencyError:
        print(
            "  ! circular FK detected; using name order "
            "(FKs are disabled during load so this is safe)",
            file=sys.stderr,
        )
        return sorted(md.tables.values(), key=lambda t: t.name)
