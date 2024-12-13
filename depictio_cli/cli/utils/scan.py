from typing import List
import typer
import os
import re
from datetime import datetime

from depictio_cli.logging import logger
from depictio_cli.cli.utils.scan import scan_runs
from depictio_models.models.workflow import WorkflowConfig, WorkflowRun



def regex_match(root, file, full_regex, data_collection):
    # Normalize the regex pattern to match both types of path separators
    normalized_regex = full_regex.replace("/", "\/")
    logger.debug(f"Root: {root}, File: {file}, Full Regex: {full_regex}, Data Collection type: {data_collection.config.regex.type.lower()}")
    # If regex pattern is file-based, match the file name directly
    if data_collection.config.regex.type.lower() == "file-based":
        if re.match(normalized_regex, file):
            logger.debug(f"Matched file - file-based: {file}")
            return True, re.match(normalized_regex, file)
    elif data_collection.config.regex.type.lower() == "path-based":
        # If regex pattern is path-based, match the full path
        file_location = os.path.join(root, file)
        if re.match(normalized_regex, file_location):
            return True, re.match(normalized_regex, file)
    return False, None

# FIXME: update model & function using a list of dict instead of a dict
def construct_full_regex(files_regex, regex_config):
    """
    Construct the full regex using the wildcards defined in the config.
    """
    for wildcard in regex_config.wildcards:
        logger.debug(f"Wildcard: {wildcard}")
        placeholder = f"{{{wildcard.name}}}"  # e.g. {date}
        regex_pattern = wildcard.wildcard_regex
        files_regex = files_regex.replace(placeholder, f"({regex_pattern})")
        logger.debug(f"Files Regex: {files_regex}")
    return files_regex

from depictio_cli.cli.utils.db import upsert_file, file_exists

def scan_files(run_location: str, run_id: str, data_collection: DataCollection) -> List[File]:
    """
    Scan the files for a given workflow and update the local TinyDB.
    """
    logger.debug(f"Scanning files in {run_location}")

    if not os.path.exists(run_location):
        raise ValueError(f"The directory '{run_location}' does not exist.")
    if not os.path.isdir(run_location):
        raise ValueError(f"'{run_location}' is not a directory.")

    file_list = list()

    logger.debug(f"Data Collection: {data_collection}")
    logger.debug(f"Regex Pattern: {data_collection.config.regex.pattern}")
    logger.debug(f"Wildcards: {data_collection.config.regex.wildcards}")

    # Construct the full regex using the wildcards defined in the config
    full_regex = (
        construct_full_regex(data_collection.config.regex.pattern, data_collection.config.regex)
        if data_collection.config.regex.wildcards
        else data_collection.config.regex.pattern
    )

    logger.debug(f"Full Regex: {full_regex}")

    # Scan the files
    for root, dirs, files in os.walk(run_location):
        for file in files:
            match, result = regex_match(root, file, full_regex, data_collection)
            if match:
                file_location = os.path.join(root, file)
                filename = file
                creation_time_float = os.path.getctime(file_location)
                modification_time_float = os.path.getmtime(file_location)

                # Convert timestamps to ISO strings
                creation_time_iso = datetime.fromtimestamp(creation_time_float).strftime("%Y-%m-%d %H:%M:%S")
                modification_time_iso = datetime.fromtimestamp(modification_time_float).strftime("%Y-%m-%d %H:%M:%S")

                file_instance = File(
                    filename=filename,
                    file_location=file_location,
                    creation_time=creation_time_iso,
                    modification_time=modification_time_iso,
                    data_collection=data_collection,
                    run_id=run_id,
                )
                logger.debug(f"File Instance: {file_instance}")

                # Check if file already exists in the local database
                if not file_exists(file_location, data_collection.id):
                    logger.info(f"Registering new file: {file_location}")
                    upsert_file(file_location, file_instance.dict())
                else:
                    logger.info(f"File already exists: {file_location}")

                file_list.append(file_instance)

    logger.debug(f"File List: {file_list}")
    return file_list


from depictio_cli.cli.utils.db import upsert_run

def scan_runs(
    parent_runs_location,
    workflow_config: WorkflowConfig,
    data_collection: DataCollection,
    workflow_id: str,
) -> List[WorkflowRun]:
    """
    Scan the runs for a given workflow and update the local TinyDB.
    """
    if not os.path.exists(parent_runs_location):
        raise ValueError(f"The directory '{parent_runs_location}' does not exist.")
    if not os.path.isdir(parent_runs_location):
        raise ValueError(f"'{parent_runs_location}' is not a directory.")

    runs = list()

    for run in os.listdir(parent_runs_location):
        if os.path.isdir(os.path.join(parent_runs_location, run)):
            if re.match(workflow_config.runs_regex, run):
                run_location = os.path.join(parent_runs_location, run)
                files = scan_files(run_location=run_location, run_id=run, data_collection=data_collection)
                execution_time = datetime.fromtimestamp(os.path.getctime(run_location))

                workflow_run = WorkflowRun(
                    workflow_id=workflow_id,
                    run_tag=run,
                    files=files,
                    workflow_config=workflow_config,
                    run_location=run_location,
                    execution_time=execution_time,
                    execution_profile=None,
                )

                # Upsert the workflow run into the local database
                upsert_run(run, workflow_run.dict())

                runs.append(workflow_run)

    return runs


from depictio_cli.db import upsert_file, upsert_run, file_exists
from datetime import datetime
import os


def scan_files_for_data_collection(
    project_config: dict, 
    workflow_id: str, 
    data_collection_id: str, 
    headers: dict, 
    scan_type: str = "scan"
) -> None:
    """
    Scan files for a given data collection of a workflow and track progress in the local TinyDB.

    Args:
        project_config (dict): The project configuration dictionary.
        workflow_id (str): The ID of the workflow.
        data_collection_id (str): The ID of the data collection.
        headers (dict): Authorization headers for API requests.
        scan_type (str): The type of scan to perform. Default is "scan".
    """
    logger.info(f"Scanning files for data collection {data_collection_id} of workflow {workflow_id}...")

    # Retrieve workflow and data collection details
    logger.debug("Fetching workflow and data collection details from local configurations...")
    workflow = project_config["workflows"].get(workflow_id)
    if not workflow:
        logger.error(f"Workflow {workflow_id} not found in project configuration.")
        raise typer.Exit(code=1)

    data_collection = next(
        (dc for dc in workflow["data_collections"] if dc["_id"] == data_collection_id), 
        None
    )
    if not data_collection:
        logger.error(f"Data collection {data_collection_id} not found in workflow {workflow_id}.")
        raise typer.Exit(code=1)

    logger.info(f"Found data collection: {data_collection['name']}")

    # Retrieve locations from the workflow config
    locations = workflow["config"].get("parent_runs_location", [])
    if not locations:
        logger.warning(f"No locations configured for workflow {workflow_id}.")
        return

    # Process each location
    for location in locations:
        logger.info(f"Scanning location: {location}")
        try:
            # Scan the runs and retrieve the files
            runs_and_content = scan_runs(location, workflow["config"], data_collection, workflow_id)

            for run in runs_and_content:
                files = run.pop("files", [])

                # Save or update run in the local database
                logger.info(f"Upserting run {run['run_tag']} to local database.")
                upsert_run(run["run_tag"], run)

                # Save or update files in the local database
                for file in files:
                    file_location = file.file_location
                    if not file_exists(file_location, data_collection_id):
                        logger.info(f"Registering new file: {file_location}")
                        upsert_file(file_location, file.dict())
                    else:
                        logger.info(f"File already exists: {file_location}")
        except Exception as e:
            logger.error(f"Error scanning location {location}: {e}")

    logger.info(f"Completed scanning files for data collection {data_collection_id}.")
