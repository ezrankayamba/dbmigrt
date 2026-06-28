"""Command-line interface for app.

The CLI is intentionally thin: it resolves a source and destination from the
registries and delegates all real work to them. Adding an engine never
requires editing this file — the --from/--to choices come from the registry
keys.
"""

import os

import click

from . import __version__
from .sources import SOURCES
from .destinations import DESTINATIONS


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="dbmigrt")
def cli():
    """dbmigrt — pluggable database migrator.

    \b
    Currently supported:
      source:      mysql
      destination: mssql
    """


@cli.command()
@click.option("--from", "source", default="mysql", show_default=True,
              type=click.Choice(list(SOURCES)), help="Source engine.")
@click.option("--to", "dest", default="mssql", show_default=True,
              type=click.Choice(list(DESTINATIONS)), help="Destination engine.")
@click.option("--url", required=True, metavar="URL",
              help="Source SQLAlchemy URL, e.g. mysql+pymysql://user:pass@host/db")
@click.option("--out", default="./out", show_default=True,
              type=click.Path(file_okay=False),
              help="Output directory for schema.sql and data.sql.")
def export(source, dest, url, out):
    """Connect to the source and write schema.sql + data.sql."""
    src, dst = SOURCES[source], DESTINATIONS[dest]
    os.makedirs(out, exist_ok=True)
    click.echo(f"Reflecting {source} at {url} ...")
    engine, md = src.reflect(url)
    click.echo(f"  found {len(md.tables)} tables")
    dst.write_schema(os.path.join(out, "schema.sql"), md)
    dst.write_data(os.path.join(out, "data.sql"), engine, md)
    views = src.reflect_views(engine)
    if views:
        dst.write_views(os.path.join(out, "views.sql"), views)
    else:
        click.echo("  no views found")
    click.secho("Export complete.", fg="green")


@cli.command()
@click.option("--to", "dest", default="mssql", show_default=True,
              type=click.Choice(list(DESTINATIONS)), help="Destination engine.")
@click.option("--in", "indir", default="./out", show_default=True,
              type=click.Path(exists=True, file_okay=False),
              help="Directory containing schema.sql and data.sql.")
@click.option("--url", "url", metavar="URL",
              help="Destination SQLAlchemy URL (direct-connect mode).")
@click.option("--client", is_flag=True,
              help="Use the destination client binary (e.g. sqlcmd) instead of a driver.")
@click.option("-S", "server", help="Client server (with --client).")
@click.option("-d", "database", help="Client database (with --client).")
@click.argument("extra", nargs=-1)
def push(dest, indir, url, client, server, database, extra):
    """Apply schema.sql + data.sql to the destination.

    \b
    Pick ONE mode:
      --url URL                 direct connect via a driver
      --client -S host -d db    use the destination client binary

    Trailing args after `--` pass through to the client, e.g.::

        dbmigrt push --in ./out --client -S host -d db -- -U sa -P secret
    """
    dst = DESTINATIONS[dest]
    files = [os.path.join(indir, "schema.sql"), os.path.join(indir, "data.sql")]
    for fp in files:
        if not os.path.exists(fp):
            raise click.ClickException(f"missing {fp}; run `export` first")
    # views are optional and applied last (they may depend on tables + data)
    views_file = os.path.join(indir, "views.sql")
    if os.path.exists(views_file):
        files.append(views_file)

    if client:
        if not (server and database):
            raise click.UsageError("--client requires -S <server> and -d <database>")
        dst.push_client(files, server, database, extra)
    else:
        if not url:
            raise click.UsageError("provide --url <url>, or use --client")
        dst.push_direct(url, files)
    click.secho("Push complete.", fg="green")


def main():
    cli()


if __name__ == "__main__":
    main()
