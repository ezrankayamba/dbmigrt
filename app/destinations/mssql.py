"""SQL Server (MSSQL) destination."""

import os
import subprocess
import sys

from sqlalchemy import create_engine, select, text
from sqlalchemy.dialects import mssql
from sqlalchemy.schema import CreateTable, CreateIndex

from .base import Destination
from ..ordering import ordered_tables

BATCH = 1000  # SQL Server hard cap for multi-row VALUES inserts


class MSSQLDestination(Destination):
    """Generate and apply SQL Server-compatible schema and data.

    Key behaviours:
      * Primary-key / Id values are preserved exactly via SET IDENTITY_INSERT
        plus inlined literal values, so foreign-key references stay valid.
      * FK constraints are disabled across the whole data load and
        re-validated afterwards, making table load order non-fragile.
      * INSERTs are batched (<=1000 rows) to respect the T-SQL VALUES limit.
    """

    name = "mssql"
    dialect = mssql.dialect()

    # -- helpers ----------------------------------------------------------- #
    @staticmethod
    def _has_identity(table):
        """True if the table has a single auto-increment integer PK."""
        pk = list(table.primary_key.columns)
        return (
            len(pk) == 1
            and bool(pk[0].autoincrement)
            and str(pk[0].type).upper().startswith(
                ("INT", "BIGINT", "SMALLINT", "TINYINT")
            )
        )

    @staticmethod
    def _split_batches(sql_text):
        """Split a script into batches on lines containing only GO."""
        batches, current = [], []
        for line in sql_text.splitlines():
            if line.strip().upper() == "GO":
                if current:
                    batches.append("\n".join(current))
                    current = []
            else:
                current.append(line)
        if current:
            batches.append("\n".join(current))
        return [b for b in batches if b.strip()]

    # -- schema ------------------------------------------------------------ #
    def write_schema(self, path, md):
        d = self.dialect
        with open(path, "w", encoding="utf-8") as f:
            f.write("SET NOCOUNT ON;\nGO\n\n/* ===== SCHEMA ===== */\n")
            for table in ordered_tables(md):
                ddl = str(CreateTable(table).compile(dialect=d)).strip()
                f.write(f"\n/* --- {table.name} --- */\n{ddl};\nGO\n")
                for idx in table.indexes:
                    f.write(
                        str(CreateIndex(idx).compile(dialect=d)).strip()
                        + ";\nGO\n"
                    )
        print(f"  wrote {path}")

    # -- data -------------------------------------------------------------- #
    def write_data(self, path, engine, md):
        d = self.dialect
        tables = ordered_tables(md)
        with engine.connect() as conn, open(path, "w", encoding="utf-8") as f:
            f.write("SET NOCOUNT ON;\nGO\n\n")
            f.write("/* ===== DISABLE FOREIGN KEYS ===== */\n")
            for t in tables:
                f.write(f"ALTER TABLE [{t.name}] NOCHECK CONSTRAINT ALL;\n")
            f.write("GO\n\n/* ===== DATA ===== */\n")

            for table in tables:
                ident = self._has_identity(table)
                cols = [c.name for c in table.columns]
                f.write(f"\n/* --- {table.name} --- */\n")
                if ident:
                    f.write(f"SET IDENTITY_INSERT [{table.name}] ON;\nGO\n")

                def flush(rows):
                    ins = table.insert().values(rows)
                    f.write(
                        str(
                            ins.compile(
                                dialect=d,
                                compile_kwargs={"literal_binds": True},
                            )
                        )
                        + ";\nGO\n"
                    )

                batch, total = [], 0
                result = conn.execution_options(stream_results=True).execute(
                    select(table)
                )
                for row in result:
                    batch.append(dict(zip(cols, row)))
                    if len(batch) == BATCH:
                        flush(batch)
                        total += len(batch)
                        batch = []
                if batch:
                    flush(batch)
                    total += len(batch)

                if ident:
                    f.write(f"SET IDENTITY_INSERT [{table.name}] OFF;\nGO\n")
                print(f"  {table.name}: {total} rows")

            f.write("\n/* ===== RE-ENABLE FOREIGN KEYS ===== */\n")
            for t in tables:
                f.write(
                    f"ALTER TABLE [{t.name}] WITH CHECK CHECK CONSTRAINT ALL;\n"
                )
            f.write("GO\n")
        print(f"  wrote {path}")

    # -- views ------------------------------------------------------------- #
    @staticmethod
    def _translate_view_sql(create_sql):
        """Best-effort MySQL -> MSSQL identifier translation for view bodies.

        Converts backtick-quoted identifiers to bracket-quoted ones. This
        handles the common case; complex view SQL (functions, LIMIT, etc.) may
        still need manual review, which is flagged in the output file.
        """
        out, i, n = [], 0, len(create_sql)
        while i < n:
            ch = create_sql[i]
            if ch == "`":
                j = create_sql.find("`", i + 1)
                if j == -1:
                    out.append(ch); i += 1; continue
                out.append("[" + create_sql[i + 1:j] + "]")
                i = j + 1
            else:
                out.append(ch); i += 1
        return "".join(out)

    def write_views(self, path, views):
        with open(path, "w", encoding="utf-8") as f:
            f.write("SET NOCOUNT ON;\nGO\n\n/* ===== VIEWS ===== */\n")
            f.write("/* NOTE: view bodies are translated best-effort from the "
                    "source dialect.\n   Review complex expressions (functions, "
                    "LIMIT/TOP, date functions) manually. */\n")
            for name, create_sql in views:
                translated = self._translate_view_sql(create_sql)
                f.write(f"\n/* --- {name} --- */\n")
                # CREATE VIEW must be the first statement in its batch
                f.write(f"{translated};\nGO\n")
        print(f"  wrote {path} ({len(views)} views)")
        return len(views)

    # -- push -------------------------------------------------------------- #
    def push_direct(self, url, files):
        engine = create_engine(url)
        with engine.begin() as conn:
            for path in files:
                print(f"  applying {path} ...")
                sql = open(path, encoding="utf-8").read()
                for i, batch in enumerate(self._split_batches(sql), 1):
                    try:
                        conn.execute(text(batch))
                    except Exception as e:
                        print(
                            f"    ! batch {i} in {os.path.basename(path)} "
                            f"failed: {e}",
                            file=sys.stderr,
                        )
                        raise

    def push_client(self, files, server, database, extra):
        for path in files:
            cmd = [
                "sqlcmd", "-S", server, "-d", database,
                "-f", "65001", "-b", "-i", path,
            ] + list(extra)
            print("  $ " + " ".join(cmd))
            subprocess.run(cmd, check=True)
