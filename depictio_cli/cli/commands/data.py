from depictio_cli.cli.utils.config import validate_and_prepare
from depictio_cli.cli.utils.data_collections import process_data_collection_helper
from depictio_cli.cli.utils.workflows import create_update_delete_workflow, process_workflow_helper
import typer
from typing import Annotated, Optional

from depictio_cli.logging import logger

app = typer.Typer()




@app.command()
def setup(
    CLI_config_path: Annotated[str, typer.Option("--CLI-config-path", help="Path to the CLI configuration file")] = "~/.depictio/CLI.yaml",
    project_config_path: Annotated[str, typer.Option("--project-config-path", help="Path to the pipeline configuration file")] = "",
    update: Optional[bool] = typer.Option(False, "--update", help="Update the workflow if it already exists"),
    # erase_all: Optional[bool] = typer.Option(False, "--erase-all", help="Erase all workflows and data collections"),
    scan_files: Optional[bool] = typer.Option(False, "--scan-files", help="Scan files for all data collections of the workflow"),
    data_collection_tag: Optional[str] = typer.Option(None, "--data-collection-tag", help="Data collection tag to be scanned"),
):
    """
    
    """
    # Step 1: Validate configurations and prepare headers
    project_config, headers, cli_config = validate_and_prepare(CLI_config_path, project_config_path)
    logger.debug(f"Project config: {project_config}")

    # Populate DB with the validated config for each workflow
    for workflow in project_config["workflows"]:
        logger.info(f"Processing workflow: {workflow['engine']}/{workflow['name']}")
        response_body = create_update_delete_workflow(project_config, workflow, headers, cli_config, update=update)
        logger.debug(f"Response body: {response_body}")

        process_workflow_helper(cli_config, response_body, headers, scan_files=scan_files, data_collection_tag=data_collection_tag)

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
    validated_config, headers, cli_config = validate_and_prepare(CLI_config_path, pipeline_config_path)

    # Step 2: Process data collections for the tag
    for workflow in validated_config["workflows"]:
        logger.info(f"Processing workflow: {workflow['name']}")
        for dc in workflow["data_collections"]:
            logger.info(f"Processing data collection: {dc['name']}")
            if data_collection_tag and dc["data_collection_tag"] == data_collection_tag:
                logger.info(f"BINGO - Processing data collection with tag: {data_collection_tag}")
                process_data_collection_helper(cli_config, workflow["_id"], dc, headers)
