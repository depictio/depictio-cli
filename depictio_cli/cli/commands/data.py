import typer
from typing import Annotated, Optional

from depictio_cli.cli.utils.api_calls import api_get_project_from_id
from depictio_cli.cli.utils.projects import process_project_helper
from depictio_cli.logging import logger
from depictio_cli.cli.utils.rich_utils import rich_print_checked_statement, rich_print_command_usage
from depictio_cli.cli.utils.config import validate_project_config_and_check_S3_storage
from depictio_models.models.cli import CLIConfig

app = typer.Typer()


@app.command()
def scan(
    CLI_config_path: Annotated[str, typer.Option("--CLI-config-path", help="Path to the CLI configuration file")] = "~/.depictio/CLI.yaml",
    project_config_path: Annotated[str, typer.Option("--project-config-path", help="Path to the pipeline configuration file")] = "",
    workflow_name: Annotated[str, typer.Option("--workflow-name", help="Name of the workflow to be scanned")] = None,
    data_collection_tag: Annotated[str, typer.Option("--data-collection-tag", help="Data collection tag to be scanned")] = None,
    reprocess_runs: bool = typer.Option(False, "--reprocess-runs", help="Reprocess all runs for the data collection"),
    update_files: bool = typer.Option(False, "--update-files", help="Update files for the data collection"),
):
    """
    Scan files.

    Args:
        CLI_config_path (Annotated[str, typer.Option, optional): _description_. Defaults to "Path to the CLI configuration file")]="~/.depictio/CLI.yaml".
        project_config_path (Annotated[str, typer.Option, optional): _description_. Defaults to "Path to the pipeline configuration file")]="".
        workflow_name (Annotated[str, typer.Option, optional): _description_. Defaults to "Name of the workflow to be scanned")]="",
        data_collection_tag (Optional[str], optional): _description_. Defaults to typer.Option(None, "--data-collection-tag", help="Data collection tag to be scanned").
        reprocess_runs (Annotated[bool, typer.Option, optional): _description_. Defaults to "Reprocess all runs for the data collection")]=False.
        update_files (Annotated[bool, typer.Option, optional): _description_. Defaults to "Update files for the data collection")]=False.
    """
    rich_print_command_usage("scan")

    logger.info(f"Reprocessing runs: {reprocess_runs}")
    logger.info(f"Updating files: {update_files}")
    # Validate configurations and prepare headers
    CLI_config, response = validate_project_config_and_check_S3_storage(CLI_config_path=CLI_config_path, project_config_path=project_config_path)

    if response["success"]:
        rich_print_checked_statement("Depictio Project configuration validated", "success")

        # Get the validated project configuration
        project_config = response["project_config"]

        # Get remote project configuration
        remote_project_config = api_get_project_from_id(str(project_config.id), CLI_config)

        if remote_project_config.status_code == 200:
            logger.info("Remote project configuration fetched successfully.")
            rich_print_checked_statement("Remote project configuration fetched successfully.", "success")

            # project_config = project_config.mongo()

            # Compare hashes
            local_hash = project_config.hash
            remote_hash = remote_project_config.json().get("hash", None)
            logger.info(f"Local & Remote hashes: {local_hash} & {remote_hash}")
            comparison_result = local_hash == remote_hash

            if comparison_result:
                rich_print_checked_statement("Local and remote project configurations match.", "success")

                # Process project
                process_project_helper(
                    CLI_config=CLI_config,
                    project_config=project_config,
                    workflow_name=workflow_name,
                    data_collection_tag=data_collection_tag,
                    reprocess_runs=reprocess_runs,
                    update_files=update_files,
                )

            else:
                rich_print_checked_statement("Local and remote project configurations do not match.", "error")
        else:
            rich_print_checked_statement("Error fetching remote project configuration. Please create the project first if it does not exist.", "error")

    else:
        rich_print_checked_statement("Depictio Project configuration validation failed", "error")

    # Step 2: Process project
    # process_project_helper(cli_config, project_config, headers, update, scan_files, data_collection_tag)

    # remote_upload_files(response["CLI_config"], project_config_path, data_collection_tag)


@app.command()
def setup(
    CLI_config_path: Annotated[str, typer.Option("--CLI-config-path", help="Path to the CLI configuration file")] = "~/.depictio/CLI.yaml",
    project_config_path: Annotated[str, typer.Option("--project-config-path", help="Path to the pipeline configuration file")] = "",
    update: Optional[bool] = typer.Option(False, "--update", help="Update the workflow if it already exists"),
    # erase_all: Optional[bool] = typer.Option(False, "--erase-all", help="Erase all workflows and data collections"),
    scan_files: Optional[bool] = typer.Option(False, "--scan-files", help="Scan files for all data collections of the workflow"),
    data_collection_tag: Optional[str] = typer.Option(None, "--data-collection-tag", help="Data collection tag to be scanned"),
):
    """ """
    # Step 1: Validate configurations and prepare headers
    # project_config, headers, cli_config = login_and_validate_project_config(CLI_config_path, project_config_path)
    # logger.debug(f"Project config: {project_config}")

    # Step 2: Process project
    # process_project_helper(cli_config, project_config, headers, update, scan_files, data_collection_tag)

    # remote_upload_files(response["CLI_config"], project_config_path, data_collection_tag)


@app.command()
def process_data_collection(
    CLI_config_path: Annotated[str, typer.Option("--CLI-config-path", help="Path to the CLI configuration file")] = "~/.depictio/CLI.yaml",
    pipeline_config_path: Annotated[str, typer.Option("--project-config-path", help="Path to the pipeline configuration file")] = "",
    data_collection_tag: Optional[str] = typer.Option(None, "--data-collection-tag", help="Data collection tag to be processed"),
):
    """
    Process data collections for a specific tag.
    """
    # Step 1: Validate configurations and prepare headers
    # # validated_config, headers, cli_config =
    # # validated_config, headers, cli_config = login_and_validate_project_config(CLI_config_path, pipeline_config_path)

    # # Step 2: Process data collections for the tag
    # for workflow in validated_config["workflows"]:
    #     logger.info(f"Processing workflow: {workflow['name']}")
    #     for dc in workflow["data_collections"]:
    #         logger.info(f"Processing data collection: {dc['name']}")
    #         if data_collection_tag and dc["data_collection_tag"] == data_collection_tag:
    #             logger.info(f"BINGO - Processing data collection with tag: {data_collection_tag}")
    #             process_data_collection_helper(cli_config, workflow["_id"], dc, headers)
    pass
