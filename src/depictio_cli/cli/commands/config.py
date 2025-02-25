import typer
from typing import Annotated

from depictio_models.utils import convert_model_to_dict
from depictio_cli.logging import logger
from depictio_cli.cli.utils.api_calls import (
    api_check_server_status,
    api_get_project_from_name,
    api_sync_project_config_to_server,
)
from depictio_cli.cli.utils.common import load_depictio_config
from depictio_cli.cli.utils.config import validate_project_config_and_check_S3_storage
from depictio_cli.cli.utils.s3 import S3_storage_checks
from depictio_cli.cli.utils.rich_utils import (
    rich_print_checked_statement,
    rich_print_json,
    rich_print_command_usage,
)

app = typer.Typer()


@app.command()
def show_cli_config(
    CLI_config_path: Annotated[
        str, typer.Option("--CLI-config-path", help="Path to the configuration file")
    ] = "~/.depictio/CLI.yaml",
):
    """
    Show the current Depictio CLI configuration.

    Args:
        CLI_config_path (Annotated[str, typer.Option, optional): _description_. Defaults to "Path to the configuration file")]="~/.depictio/CLI.yaml".
    """
    # Display command usage in a styled panel

    rich_print_command_usage("show_cli_config")

    try:
        depictio_CLI_config = load_depictio_config(yaml_config_path=CLI_config_path)
        logger.debug(f"depictio_CLI_config: {depictio_CLI_config}")
        rich_print_json(
            "Current Depictio CLI Configuration: ",
            convert_model_to_dict(depictio_CLI_config),
        )
    except Exception as e:
        rich_print_checked_statement(f"Unable to load configuration - {e}", "error")


@app.command()
def check_s3_storage(
    CLI_config_path: Annotated[
        str, typer.Option("--CLI-config-path", help="Path to the configuration file")
    ] = "~/.depictio/CLI.yaml",
):
    """
    Check the S3 storage configuration provided in the CLI configuration file.

    Args:
        CLI_config_path (Annotated[str, typer.Option, optional): _description_. Defaults to "Path to the configuration file")]="~/.depictio/CLI.yaml".
    """
    rich_print_command_usage("check_S3_storage")
    try:
        CLI_config = load_depictio_config(yaml_config_path=CLI_config_path)
        s3_response = S3_storage_checks(CLI_config)
        if s3_response:
            rich_print_checked_statement(
                "S3 storage configuration is correct", "success"
            )
        else:
            rich_print_checked_statement(
                "S3 storage configuration is incorrect", "error"
            )
    except Exception as e:
        rich_print_checked_statement(f"Unable to check S3 storage - {e}", "error")


@app.command()
def check_server_accessibility(
    CLI_config_path: Annotated[
        str, typer.Option("--CLI-config-path", help="Path to the configuration file")
    ] = "~/.depictio/CLI.yaml",
):
    """
    Check if the server is accessible.

    Args:
        CLI_config_path (Annotated[str, typer.Option, optional): _description_. Defaults to "Path to the configuration file")]="~/.depictio/CLI.yaml".
    """
    rich_print_command_usage("check_server_accessibility")
    try:
        CLI_config = load_depictio_config(yaml_config_path=CLI_config_path)
        response = api_check_server_status(CLI_config)
        if response.status_code == 200:
            rich_print_checked_statement("Server is accessible", "success")
        else:
            rich_print_checked_statement("Server is not accessible", "error")

    except Exception as e:
        rich_print_checked_statement(f"Unable to access server - {e}", "error")


@app.command()
def show_depictio_project_metadata_on_server(
    CLI_config_path: Annotated[
        str, typer.Option("--CLI-config-path", help="Path to the configuration file")
    ] = "~/.depictio/CLI.yaml",
    project_name: Annotated[
        str, typer.Option("--project-name", help="Name of the project")
    ] = "",
):
    """
    Show Depictio metadata for registered Depictio projects in the JSON format.
    """
    rich_print_command_usage("show_depictio_json_metadata")
    try:
        CLI_config = load_depictio_config(yaml_config_path=CLI_config_path)
        project_metadata = api_get_project_from_name(project_name, CLI_config)
        metadata = project_metadata.json()
        rich_print_json(
            "Depictio metadata for registered Depictio projects: ", metadata
        )
    except Exception as e:
        rich_print_checked_statement(f"Unable to load metadata - {e}", "error")


@app.command()
def validate_project_config(
    CLI_config_path: Annotated[
        str, typer.Option("--CLI-config-path", help="Path to the configuration file")
    ] = "~/.depictio/CLI.yaml",
    project_config_path: Annotated[
        str,
        typer.Option(
            "--project-config-path", help="Path to the pipeline configuration file"
        ),
    ] = "",
):
    """
    Validate the Depictio Project configuration.

    Args:
        CLI_config_path (Annotated[str, typer.Option, optional): _description_. Defaults to "Path to the configuration file")]="~/.depictio/CLI.yaml".
        project_config_path (Annotated[str, typer.Option, optional): _description_. Defaults to "Path to the pipeline configuration file")]="",
    """
    rich_print_command_usage("validate_project_config")
    # try:
    CLI_config, response = validate_project_config_and_check_S3_storage(
        CLI_config_path=CLI_config_path, project_config_path=project_config_path
    )
    if response["success"]:
        rich_print_checked_statement(
            "Depictio Project configuration validated", "success"
        )
        project_config = convert_model_to_dict(response["project_config"])
        rich_print_json("Validated Depictio Project Configuration: ", project_config)
    else:
        rich_print_checked_statement(
            "Pipeline configuration invalid, use --verbose for more details.", "error"
        )


@app.command()
def sync_project_config_to_server(
    CLI_config_path: Annotated[
        str, typer.Option("--CLI-config-path", help="Path to the configuration file")
    ] = "~/.depictio/CLI.yaml",
    project_config_path: Annotated[
        str,
        typer.Option(
            "--project-config-path", help="Path to the pipeline configuration file"
        ),
    ] = "",
    update: Annotated[
        bool,
        typer.Option("--update", help="Update the project configuration on the server"),
    ] = False,
):
    """
    Sync the Depictio project configuration to the server.

    Args:
        CLI_config_path (Annotated[str, typer.Option, optional): _description_. Defaults to "Path to the configuration file")]="~/.depictio/CLI.yaml".
        project_config_path (Annotated[str, typer.Option, optional): _description_. Defaults to "Path to the pipeline configuration file")]="",
        update (Annotated[bool, typer.Option, optional): _description_. Defaults to "Update the project configuration on the server")]=False.
    """
    CLI_config, validation_response = validate_project_config_and_check_S3_storage(
        CLI_config_path=CLI_config_path, project_config_path=project_config_path
    )
    if not validation_response["success"]:
        rich_print_checked_statement(
            "Pipeline configuration invalid, use --verbose for more details.", "error"
        )
        return
    rich_print_checked_statement("Pipeline configuration validated", "success")
    project_config = convert_model_to_dict(validation_response["project_config"])
    api_sync_project_config_to_server(
        CLI_config=CLI_config, ProjectConfig=project_config, update=update
    )
