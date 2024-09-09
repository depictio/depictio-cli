import hashlib
import time
import httpx
from depictio_cli.utils import create_update_delete_workflow, login, process_workflow, remote_validate_pipeline_config
import typer
from typing import Annotated, Optional

from depictio_cli.logging import logger

app = typer.Typer()


@app.command()
def validate_pipeline_config(
    agent_config_path: Annotated[str, typer.Option("--agent-config-path", help="Path to the configuration file")] = "~/.depictio/agent.yaml",
    # workflow_tag: Optional[str] = typer.Option(None, "--workflow_tag", help="Workflow name to be created"),
    # update: Optional[bool] = typer.Option(False, "--update", help="Update the workflow if it already exists"),
    # erase_all: Optional[bool] = typer.Option(False, "--erase_all", help="Erase all workflows and data collections"),
    # scan_files: Optional[bool] = typer.Option(False, "--scan_files", help="Scan files for all data collections of the workflow"),
    # data_collection_tag: Optional[str] = typer.Option(None, "--data_collection_tag", help="Data collection tag to be scanned"),
    # token: Optional[str] = typer.Option(
    #     None,  # Default to None (not specified)
    #     "--token",
    #     help="Optionally specify a token to be used for authentication",
    # ),
):
    """
    Create a new workflow from a given YAML configuration file.
    """
    logger.info(f"Creating workflow from {agent_config_path}...")

    from depictio_cli.utils import login, remote_validate_pipeline_config

    response = login()
    logger.info(response)

    if response["success"]:
        remote_validate_pipeline_config(response["agent_config"], agent_config_path)

        logger.info("Workflow created.")
    else:
        raise typer.Exit(code=1)


@app.command()
def setup(
    agent_config_path: Annotated[str, typer.Option("--agent-config-path", help="Path to the agent configuration file")] = "~/.depictio/agent.yaml",
    pipeline_config_path: Annotated[str, typer.Option("--pipeline-config-path", help="Path to the pipeline configuration file")] = "",
    update: Optional[bool] = typer.Option(False, "--update", help="Update the workflow if it already exists"),
    erase_all: Optional[bool] = typer.Option(False, "--erase-all", help="Erase all workflows and data collections"),
    scan_files: Optional[bool] = typer.Option(False, "--scan-files", help="Scan files for all data collections of the workflow"),
    data_collection_tag: Optional[str] = typer.Option(None, "--data-collection-tag", help="Data collection tag to be scanned"),
):
    """
    Upload files to a data collection.
    """
    validated_config = None
    login_response = login(agent_config_path)
    logger.info(login_response)


    if login_response["success"]:
        response = remote_validate_pipeline_config(login_response["agent_config"], pipeline_config_path)

        token = login_response["agent_config"]["user"]["token"]["access_token"]
        # hash the token
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        logger.info(f"Token hash: {token_hash}")

        if response["success"]:
            logger.info("Pipeline configuration validated.")
            validated_config = response["config"]
            logger.info(f"Validated config: {validated_config}")
        else:
            logger.info("Pipeline configuration validation failed.")
            raise typer.Exit(code=1)

        if validated_config:
            logger.info(f"Validated config: {validated_config}")

            headers = {"Authorization": f"Bearer {login_response['agent_config']['user']['token']['access_token']}"}

            # Populate DB with the validated config for each workflow
            for workflow in validated_config["workflows"]:
                logger.info(f"Processing workflow: {workflow}")
                response_body = create_update_delete_workflow(login_response["agent_config"], workflow, headers, update=update)

                # Sleep for 5 seconds to allow the DB to update
                time.sleep(5)


                logger.info(f"Workflow processed: {str(response_body)}")


                logger.info(f"Agent config: {login_response['agent_config']}")

                # DEBUG: check if workflow was created in the DB
                response_debug = httpx.get(
                    f"{login_response['agent_config']['api_base_url']}/depictio/api/v1/workflows/get_all_workflows",
                    headers=headers,
                    timeout=30.0,
                )
                logger.info(f"DEBUG - code: {response_debug.status_code}, response: {response_debug.text}, params: {response_debug.request.url}")


                response_debug = httpx.get(
                    f"{login_response['agent_config']['api_base_url']}/depictio/api/v1/workflows/get/from_args",
                    params={"name": "mosaicatcher-pipeline", "engine": "snakemake"},
                    headers=headers,
                    timeout=30.0,
                )
                logger.info(f"DEBUG - code: {response_debug.status_code}, response: {response_debug.text}, params: {response_debug.request.url}")

                process_workflow(login_response["agent_config"], response_body, headers, scan_files=scan_files, data_collection_tag=data_collection_tag)

            # remote_upload_files(response["agent_config"], pipeline_config_path, data_collection_tag)

        else:
            raise typer.Exit(code=1)
    else:
        raise typer.Exit(code=1)
