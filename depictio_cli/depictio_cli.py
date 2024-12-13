import typer
from typer.main import get_command
from depictio_cli.cli.commands.config import app as config
from depictio_cli.cli.commands.data import app as data

app = typer.Typer()
app.add_typer(config, name="config")
app.add_typer(data, name="data")
depictiocli = get_command(app)


def main():
    app()
