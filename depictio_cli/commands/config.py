from depictio_cli.utils import load_depictio_config
import typer
from typing import Optional

app = typer.Typer()

@app.command()
def show_config():
    depictio_agent_config = load_depictio_config("~/.depictio/agent.yaml")
    typer.echo(depictio_agent_config)
