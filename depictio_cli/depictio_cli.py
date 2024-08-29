import typer

from depictio_cli.commands.config import app as config
from depictio_cli.commands.data import app as data

app = typer.Typer()
app.add_typer(config, name="config")
app.add_typer(data, name="data")


def main():
    app()
