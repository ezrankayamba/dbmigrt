"""End-to-end-ish test using SQLite as a stand-in source.

We don't require a live MySQL server in CI: SQLite reflects through the same
SQLAlchemy machinery, which exercises ordering, IDENTITY detection, FK-disable
wrapping, and batch generation in the MSSQL destination.
"""

import os

from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, String, ForeignKey,
)

from app.destinations import DESTINATIONS
from app.destinations.mssql import MSSQLDestination


def _build_sqlite(path):
    engine = create_engine(f"sqlite:///{path}")
    md = MetaData()
    parent = Table(
        "parent", md,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("name", String(50)),
    )
    child = Table(
        "child", md,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("parent_id", Integer, ForeignKey("parent.id")),
        Column("label", String(50)),
    )
    md.create_all(engine)
    with engine.begin() as conn:
        conn.execute(parent.insert(), [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}])
        conn.execute(child.insert(), [{"id": 1, "parent_id": 1, "label": "x"}])
    return engine


def test_registry_has_mssql():
    assert "mssql" in DESTINATIONS
    assert isinstance(DESTINATIONS["mssql"], MSSQLDestination)


def test_schema_and_data_generation(tmp_path):
    db = tmp_path / "src.db"
    engine = _build_sqlite(str(db))
    md = MetaData()
    md.reflect(bind=engine)

    dst = MSSQLDestination()
    schema = tmp_path / "schema.sql"
    data = tmp_path / "data.sql"
    dst.write_schema(str(schema), md)
    dst.write_data(str(data), engine, md)

    schema_sql = schema.read_text()
    data_sql = data.read_text()

    # parent must be created/inserted before child (FK order)
    assert schema_sql.index("parent") < schema_sql.index("child")
    assert data_sql.index("[parent]") < data_sql.index("[child]")

    # identity insert wrapping present for integer-PK tables
    assert "SET IDENTITY_INSERT [parent] ON" in data_sql
    assert "SET IDENTITY_INSERT [parent] OFF" in data_sql

    # FK disable / re-enable wrapping present
    assert "NOCHECK CONSTRAINT ALL" in data_sql
    assert "WITH CHECK CHECK CONSTRAINT ALL" in data_sql

    # original ids preserved as literals
    assert "1" in data_sql and "'a'" in data_sql


def test_go_batch_split():
    dst = MSSQLDestination()
    batches = dst._split_batches("SELECT 1;\nGO\nSELECT 2;\nGO\n")
    assert batches == ["SELECT 1;", "SELECT 2;"]


def test_view_translation_and_write(tmp_path):
    dst = MSSQLDestination()
    # backtick identifiers should become bracket identifiers
    translated = dst._translate_view_sql(
        "CREATE VIEW `v` AS SELECT `id` FROM `parent`")
    assert "`" not in translated
    assert "[id]" in translated and "[parent]" in translated

    out = tmp_path / "views.sql"
    n = dst.write_views(str(out), [("v", "CREATE VIEW `v` AS SELECT `id` FROM `parent`")])
    assert n == 1
    body = out.read_text()
    assert "/* --- v --- */" in body
    assert "CREATE VIEW [v]" in body
    assert body.rstrip().endswith("GO")
