import json
import sys
from depictio_models.models.cli import CLIConfig
import os, yaml, typer, httpx
from typing import Dict, Optional, Tuple, List
from depictio_cli.logging import logger




# TODO: change logic to just initiate the scan and not wait for the completion (thousands of files can take a long time)
# def scan_files_for_data_collection(project_config: dict, workflow_id: str, data_collection_id: str, headers: dict, scan_type: str = "scan") -> None:
#     """
#     Scan files for a given data collection of a workflow.
#     """

#     logger.info(f"Scanning files for data collection {data_collection_id} of workflow {workflow_id}...")

#     if not workflow_id or not data_collection_id:
#         raise HTTPException(
#             status_code=400,
#             detail="Both workflow_id and data_collection_id must be provided.",
#         )

#     if not current_user:
#         raise HTTPException(status_code=400, detail="Current user not found.")

#     logger.debug(f"Current user: {current_user}")

#     (
#         workflow_oid,
#         data_collection_oid,
#         workflow,
#         data_collection,
#         user_oid,
#     ) = validate_workflow_and_collection(
#         workflows_collection,
#         current_user.id,
#         workflow_id,
#         data_collection_id,
#     )

def scan_files_for_data_collection(cli_config: dict, workflow_id: str, data_collection_id: str, headers: dict, scan_type: str = "scan") -> None:
    """
    Scan files for a given data collection of a workflow.
    """

    logger.info(f"Scanning files for data collection {data_collection_id} of workflow {workflow_id}...")

    response = httpx.post(
        f"{cli_config['api_base_url']}/depictio/api/v1/files/{scan_type}/{workflow_id}/{data_collection_id}",
        headers=headers,
        timeout=10 * 60,  # Increase the timeout as needed
    )
    if response.status_code == 200:
        logger.info(f"Files successfully scanned for data collection {data_collection_id}!")
    else:
        logger.error(f"Error for data collection {data_collection_id}: {response.text}")
        typer.Exit(code=1)


def create_deltatable_request(cli_config: dict, workflow_id: str, data_collection_id: str, headers: dict) -> None:
    """
    Create a delta table for a given data collection of a workflow.
    """
    response = httpx.post(
        f"{cli_config['api_base_url']}/depictio/api/v1/deltatables/create/{workflow_id}/{data_collection_id}",
        headers=headers,
        timeout=60.0 * 5,  # Increase the timeout as needed
    )
    if response.status_code == 200:
        logger.info(f"Data successfully aggregated for data collection {data_collection_id}!")
    else:
        logger.error(f"Error for data collection {data_collection_id}: {response.text}")


def create_trackset(cli_config: dict, workflow_id: str, data_collection_id: str, headers: dict) -> None:
    """
    Upload the trackset to S3 for a given data collection of a workflow.
    """
    response = httpx.post(
        f"{cli_config['api_base_url']}/depictio/api/v1/jbrowse/create_trackset/{workflow_id}/{data_collection_id}",
        headers=headers,
        timeout=60.0 * 5,  # Increase the timeout as needed
    )
    if response.status_code == 200:
        logger.info(f"Trackset successfully created for data collection {data_collection_id}!")
    else:
        logger.error(f"Error for data collection {data_collection_id}: {response.text}")

    return response


def process_data_collection_helper(cli_config, wf_id, dc, headers, scan_files=True):
    if scan_files:
        scan_type = "scan"

        logger.info(f"Processing Data collection: {dc}")

        if "metatype" in dc["config"]:
            if dc["config"]["metatype"]:
                if dc["config"]["metatype"].lower() == "metadata":
                    scan_type = "scan_metadata"
        logger.info(f"Scan type: {scan_type}")
        scan_files_for_data_collection(cli_config, wf_id, dc["_id"], headers, scan_type)
        logger.info("Files uploaded.")

    if dc["config"]["type"].lower() == "table":
        # if dc["data_collection_tag"] == "mosaicatcher_samples_metadata":
        create_deltatable_request(cli_config, wf_id, dc["_id"], headers)
        logger.info("deltatable created.")

    # elif dc["config"]["type"].lower() == "jbrowse2":
    #     # # if dc["config"]["type"].lower() == "jbrowse2":
    #     #     # if scan_files:
    #     #     #     logger.info("scan_files_for_data_collection")
    #     #     #     scan_files_for_data_collection(wf_id, dc["_id"], headers)
    #     logger.info("upload_trackset_to_s3")
    #     create_trackset(cli_config, wf_id, dc["_id"], headers)

