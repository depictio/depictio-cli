
from depictio_cli.cli.utils.config import S3_storage_checks, load_depictio_config

from depictio_cli.logging import logger
import typer
from typing import Annotated, Optional

app = typer.Typer()


@app.command()
def show_config(
    CLI_config_path: Annotated[str, typer.Option("--CLI-config-path", help="Path to the configuration file")] = "~/.depictio/CLI.yaml",
):
    """
    Show the current configuration.

    Args:
        CLI_config_path (Annotated[str, typer.Option, optional): _description_. Defaults to "Path to the configuration file")]="~/.depictio/CLI.yaml".
    """
    depictio_CLI_config = load_depictio_config(config_path=CLI_config_path)
    typer.echo(depictio_CLI_config)



@app.command()
def validate_project_config(
    CLI_config_path: Annotated[str, typer.Option("--CLI-config-path", help="Path to the configuration file")] = "~/.depictio/CLI.yaml",
    project_config_path: Annotated[str, typer.Option("--project-config-path", help="Path to the pipeline configuration file")] = "",
):
    """
    Validate the pipeline configuration.
    """
    logger.info(f"Creating workflow from {CLI_config_path}...")
    logger.info(f"Validating pipeline configuration from {project_config_path}...")

    from depictio_cli.cli.utils.config import login, local_validate_project_config

    response = login(CLI_config_path)
    logger.info(response)

    if response["success"]:
        # Validate the project configuration
        local_validate_project_config(response["CLI_config"], project_config_path)
        # Check S3 accessibility
        S3_storage_checks(response["CLI_config"])
    else:
        raise typer.Exit(code=1)