from typeguard import typechecked
import httpx
import typer

# depictio-cli imports
from depictio_cli.cli.utils.common import generate_api_headers, load_depictio_config
from depictio_cli.logging import logger
from depictio_cli.cli.utils.rich_utils import rich_print_checked_statement

@typechecked
def api_login(yaml_config_path: str = "~/.depictio/agent.yaml") -> dict:
    """
    Login to the Depictio API using the CLI configuration.
    """
    depictio_CLI_config = load_depictio_config(yaml_config_path=yaml_config_path)
    logger.info(f"Depictio CLI configuration loaded: {depictio_CLI_config}")

    # Connect to depictio API
    response = httpx.post(f"{depictio_CLI_config['api_base_url']}/depictio/api/v1/cli/validate_cli_config", json=depictio_CLI_config)
    if response.status_code == 200:
        logger.info("Depictio CLI configuration is valid.")
        rich_print_checked_statement("Depictio CLI configuration is valid.", "success")
        return {"success": True, "CLI_config": depictio_CLI_config}
    else:
        logger.error(f"Depictio CLI configuration is invalid: {response.text}")
        rich_print_checked_statement(f"Depictio CLI configuration is invalid: {response.text}", "error")
        return {"success": False}


@typechecked
def api_get_project_from_id(project_id: str, CLI_config: dict):
    """
    Get a project from the server using the project ID.
    """
    # First check if the project exists on the server DB for existing IDs and if the same metadata hash is used
    response = httpx.get(f"{CLI_config['api_base_url']}/depictio/api/v1/projects/get/from_id", params={"project_id": project_id}, headers=generate_api_headers(CLI_config))
    return response


@typechecked
def api_create_project(project_config: dict, CLI_config: dict):
    """
    Create a project on the server.
    """
    logger.info(f"Creating project on server...")

    response = httpx.post(f"{CLI_config['api_base_url']}/depictio/api/v1/projects/create", json=project_config, headers=generate_api_headers(CLI_config))

    return response


@typechecked
def api_update_project(project_config: dict, CLI_config: dict):
    """
    Update a project on the server.
    """
    logger.info(f"Updating project on server...")

    response = httpx.put(f"{CLI_config['api_base_url']}/depictio/api/v1/projects/update", json=project_config, headers=generate_api_headers(CLI_config))

    return response


@typechecked
def api_sync_project_config_to_server(CLI_config: dict, project_config: dict, update: bool = False):
    """
    Sync the pipeline configuration to the server.
    """
    rich_print_checked_statement("Syncing pipeline configuration to server...", "info")

    # Check if the project exists on the server
    logger.info(f"Project configuration: {project_config}")
    # exit()
    response = api_get_project_from_id(project_config["id"], CLI_config)

    if response.status_code == 200:
        rich_print_checked_statement("Project configuration found on server", "info")
        logger.info(f"Project configuration found on server: {response.json()}")

        # If update flag is False, exit
        if not update:
            logger.error(f"Project configuration already exists on server, use --update flag to update.")
            rich_print_checked_statement("Project configuration already exists on server, use --update flag to update.", "error")
            raise typer.Exit(code=0)

        # If update flag is True, update the project on the server
        rich_print_checked_statement("--update flag set, updating project configuration on server...", "info")
        response = api_update_project(project_config, CLI_config)
        if response.status_code == 200:
            rich_print_checked_statement("Project updated on server", "success")
            logger.info(f"Project updated on server: {response.json()}")
        else:
            rich_print_checked_statement(f"Failed to update project on server: {response.text}", "error")
            logger.error(f"Failed to update project on server: {response.text}")
            raise typer.Exit(code=1)

    elif response.status_code == 404:
        logger.info("Project configuration not found on server.")
        rich_print_checked_statement("Project configuration not found on server, creating project...", "info")
        # Create the project on the server
        response = api_create_project(project_config, CLI_config)
        if response.status_code == 200:
            logger.info(f"Project created on server: {response.json()}")
            rich_print_checked_statement("Project created on server", "success")
        else:
            logger.error(f"Failed to create project on server: {response.text}")
            rich_print_checked_statement(f"Failed to create project on server: {response.text}", "error")
            raise typer.Exit(code=1)
