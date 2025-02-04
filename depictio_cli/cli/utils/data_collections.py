
from typeguard import typechecked

from depictio_cli.logging import logger
from depictio_cli.cli.utils.rich_utils import rich_print_checked_statement
from depictio_cli.cli.utils.scan import scan_files_for_data_collection
from depictio_models.models.cli import CLIConfig
from depictio_models.models.workflows import Workflow




# def create_deltatable_request(cli_config: dict, workflow_id: str, data_collection_id: str, headers: dict) -> None:
#     """
#     Create a delta table for a given data collection of a workflow.
#     """
#     response = httpx.post(
#         f"{cli_config['api_base_url']}/depictio/api/v1/deltatables/create/{workflow_id}/{data_collection_id}",
#         headers=headers,
#         timeout=60.0 * 5,  # Increase the timeout as needed
#     )
#     if response.status_code == 200:
#         logger.info(f"Data successfully aggregated for data collection {data_collection_id}!")
#     else:
#         logger.error(f"Error for data collection {data_collection_id}: {response.text}")


# def create_trackset(cli_config: dict, workflow_id: str, data_collection_id: str, headers: dict) -> None:
#     """
#     Upload the trackset to S3 for a given data collection of a workflow.
#     """
#     response = httpx.post(
#         f"{cli_config['api_base_url']}/depictio/api/v1/jbrowse/create_trackset/{workflow_id}/{data_collection_id}",
#         headers=headers,
#         timeout=60.0 * 5,  # Increase the timeout as needed
#     )
#     if response.status_code == 200:
#         logger.info(f"Trackset successfully created for data collection {data_collection_id}!")
#     else:
#         logger.error(f"Error for data collection {data_collection_id}: {response.text}")

#     return response


@typechecked
def process_data_collection_helper(CLI_config: CLIConfig, wf: Workflow, dc_id: str, rescan_folders: bool = False, update_files: bool = False) -> None:
    """_summary_

    Args:
        CLI_config (CLIConfig): _description_
        wf (Workflow): _description_
        dc_id (str): _description_
        rescan_folders (bool, optional): _description_. Defaults to False.
        update_files (bool, optional): _description_. Defaults to False.
    """
    dc = next((dc for dc in wf.data_collections if str(dc.id) == dc_id), None)
    rich_print_checked_statement(f"Processing Data collection: {dc.data_collection_tag}", "info")
    logger.info(f"Processing Data collection: {dc}")
    scan_files_for_data_collection(workflow=wf, data_collection_id=dc_id, rescan_folders=rescan_folders, update_files=update_files)
    rich_print_checked_statement(f"Data collection {dc.data_collection_tag} processed successfully", "success")

    # if dc["config"]["type"].lower() == "table":
    #     # if dc["data_collection_tag"] == "mosaicatcher_samples_metadata":
    #     create_deltatable_request(cli_config, wf_id, dc["_id"], headers)
    #     logger.info("deltatable created.")

    # elif dc["config"]["type"].lower() == "jbrowse2":
    #     # # if dc["config"]["type"].lower() == "jbrowse2":
    #     #     # if scan_files:
    #     #     #     logger.info("scan_files_for_data_collection")
    #     #     #     scan_files_for_data_collection(wf_id, dc["_id"], headers)
    #     logger.info("upload_trackset_to_s3")
    #     create_trackset(cli_config, wf_id, dc["_id"], headers)
