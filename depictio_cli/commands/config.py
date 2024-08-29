from depictio_cli.utils import load_depictio_config
import typer
from typing import Annotated, Optional

app = typer.Typer()


@app.command()
def show_config(
    agent_config_path: Annotated[str, typer.Option("--agent-config-path", help="Path to the configuration file")] = "~/.depictio/agent.yaml",
):
    depictio_agent_config = load_depictio_config(config_path=agent_config_path)
    typer.echo(depictio_agent_config)
