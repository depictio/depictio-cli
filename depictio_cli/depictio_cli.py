import typer

from depictio_cli.commands.config import app as config
# from depictio_cli.commands.upload import app as upload

app = typer.Typer()
app.add_typer(config, name="config")
# app.add_typer(upload, name="upload")


def main():
    app()
