import collections
from typing import List, Optional, Union
from bson import ObjectId
from typeguard import typechecked
import typer
import os
import re
from datetime import datetime
import hashlib

from depictio_cli.cli.utils.common import format_timestamp
from depictio_cli.cli.utils.db import DBManager
from depictio_cli.cli.utils.rich_utils import rich_print_checked_statement
from depictio_cli.logging import logger

from depictio_models.models.base import PyObjectId
from depictio_models.models.data_collections import DataCollection, Regex
from depictio_models.models.workflows import Workflow, WorkflowConfig, WorkflowDataLocation, WorkflowRun
from depictio_models.models.files import File
from depictio_models.utils import convert_model_to_dict


def regex_match(file: File, full_regex: str):
    # Normalize the regex pattern to match both types of path separators
    normalized_regex = full_regex.replace("/", "\/")
    # logger.debug(f"File: {file}, Full Regex: {full_regex}")
    if re.match(normalized_regex, file):
        logger.debug(f"Matched file - file-based: {file}")
        return True, re.match(normalized_regex, file)
    return False, None


def construct_full_regex(regex=Regex):
    """
    Construct the full regex using the wildcards defined in the config.

    Args:
        regex (Regex): The regex configuration object.
    """
    for wildcard in regex.wildcards:
        logger.debug(f"Wildcard: {wildcard}")
        placeholder = f"{{{wildcard.name}}}"  # e.g. {date}
        regex_pattern = wildcard.wildcard_regex
        files_regex = regex.replace(placeholder, f"({regex_pattern})")
        logger.debug(f"Files Regex: {files_regex}")
    return files_regex


# from depictio_cli.cli.utils.db import upsert_file, file_exists


def generate_file_hash(filename: str, filesize: int, creation_time: str, modification_time: str) -> str:
    """
    Generates a hash for the file based on its filename, size, creation time, and modification time.

    Args:
        filename (str): The name of the file.
        filesize (int): The size of the file in bytes.
        creation_time (str): The creation time in ISO format.
        modification_time (str): The modification time in ISO format.
        hash_algo (str): The hashing algorithm to use (default is 'sha256').

    Returns:
        str: The hexadecimal digest of the hash.
    """
    logger.debug(f"Generating hash for file {filename} with attributes {filesize}, {creation_time}, {modification_time}")
    # Concatenate the attributes into a single string
    hash_input = f"{filename}{filesize}{creation_time}{modification_time}".encode("utf-8")
    # Generate the hash using SHA-256
    file_hash = hashlib.sha256(hash_input).hexdigest()

    return file_hash


def generate_run_hash(run_location: str, creation_time: str, last_modification_time: str, files: List[File]) -> str:
    """
    Generates a hash for the run based on its location, creation time, and last modification time, and the files it contains.

    Args:
        run_location (str): The location of the run.
        creation_time (str): The creation time in ISO format.
        last_modification_time (str): The last modification time in ISO format.

    Returns:
        str: The hexadecimal digest of the hash.
    """
    # Create a list of file hashes, sorted by filename
    file_hashes = sorted([file.file_hash for file in files])
    # Turn the list into a hashable string
    file_hashes_str = "".join(file_hashes)
    # Hash the file hashes
    files_hash = hashlib.sha256(file_hashes_str.encode("utf-8")).hexdigest()

    # Concatenate the attributes into a single string
    hash_input = f"{run_location}{creation_time}{last_modification_time}{files_hash}".encode("utf-8")

    # Generate the hash using SHA-256
    run_hash = hashlib.sha256(hash_input).hexdigest()

    return run_hash


def check_run_differences(previous_run_entry: WorkflowRun, run_location: str, creation_time: str, last_modification_time: str, files: List[File]) -> dict:
    """_summary_

    Args:
        previous_run_entry (WorkflowRun): _description_
        run_location (str): _description_
        creation_time (str): _description_
        last_modification_time (str): _description_
        files (List[File]): _description_

    Returns:
        list: _description_
    """
    # Check if the run hash has changed
    run_hash = generate_run_hash(run_location, creation_time, last_modification_time, files)
    if previous_run_entry.hash != run_hash:
        differences = collections.defaultdict(dict)
        logger.warning(f"Hash mismatch for run {run_location}.")
        # Deconvolute the hash to identify what changed
        # Check what changed
        if run_location != previous_run_entry.run_location:
            logger.warning(f"Run location changed for run {run_location}.")
            differences["run_location"] = {"previous": previous_run_entry.run_location, "current": run_location}

        if creation_time != previous_run_entry.creation_time:
            logger.warning(f"Creation time changed for run {run_location}.")
            differences["creation_time"] = {"previous": previous_run_entry.creation_time, "current": creation_time}

        if last_modification_time != previous_run_entry.last_modification_time:
            logger.warning(f"Last modification time changed for run {run_location}.")
            differences["last_modification_time"] = {"previous": previous_run_entry.last_modification_time, "current": last_modification_time}

        # if differences is empty, then files have changed
        if not differences:
            logger.warning(f"Files changed for run {run_location}.")
            differences["files"] = {"previous": previous_run_entry.files_id, "current": [file.id for file in files]}

        return differences
    return {}


def process_files(
    path: str,
    run_id: str,
    data_collection: "DataCollection",
    existing_files: List[dict],
    update_files: bool = False,
    skip_regex: bool = False,
) -> List["File"]:
    """
    Scan files from a given directory or a single file path.

    If 'path' is a directory, scan using os.walk.
    If it's a file, process that file directly.

    Args:
        path (str): The directory or file path to scan.
        run_id (str): The ID of the run.
        data_collection (DataCollection): The data collection configuration.
        existing_files (List[dict]): The list of files already in the database.
        update_files (bool): Whether to update files that already exist.
        skip_regex (bool): Whether to skip the regex check.

    Returns:
        List[File]: A list of File instances representing the scanned files.
    """
    logger.debug(f"Scanning path: {path}")

    if not os.path.exists(path):
        raise ValueError(f"The path '{path}' does not exist.")

    file_list = []

    # For recursive scans, build the regex from configuration.
    full_regex = None
    if not skip_regex:
        regex_config = data_collection.config.scan.scan_parameters.regex_config
        full_regex = construct_full_regex(regex=regex_config) if getattr(regex_config, "wildcards", False) else regex_config.pattern
        logger.debug(f"Full Regex: {full_regex}")

    # # Get the full regex from the data collection config.
    # regex_config = data_collection.config.scan.scan_parameters.regex_config
    # full_regex = (
    #     construct_full_regex(regex=regex_config)
    #     if getattr(regex_config, "wildcards", False)
    #     else regex_config.pattern
    # )
    # logger.debug(f"Full Regex: {full_regex}")

    if os.path.isdir(path):
        logger.debug(f"Scanning directory: {path}")
        for root, _, files in os.walk(path):
            for file in files:
                file_location = os.path.join(root, file)
                file_instance = scan_single_file(
                    file_location=file_location,
                    run_id=run_id,
                    data_collection=data_collection,
                    existing_files=existing_files,
                    update_files=update_files,
                    full_regex=full_regex,
                    skip_regex=skip_regex,
                )
                if file_instance:
                    file_list.append(file_instance)
    elif os.path.isfile(path):
        logger.debug(f"Scanning single file: {path}")
        file_instance = scan_single_file(
            file_location=path,
            run_id=run_id,
            data_collection=data_collection,
            existing_files=existing_files,
            update_files=update_files,
            full_regex=full_regex,
            skip_regex=skip_regex,
        )
        if file_instance:
            file_list.append(file_instance)
    else:
        raise ValueError(f"Path '{path}' is neither a file nor a directory.")

    return file_list


def scan_single_file(
    file_location: str,
    run_id: str,
    data_collection: "DataCollection",
    existing_files: List[dict],
    update_files: bool,
    full_regex: str,
    skip_regex: bool = False,
) -> Optional["File"]:
    """
    Process a single file.

    Checks if the filename matches the regex pattern.
    If the file already exists (based on its file_location), it will skip (unless update_files is True).
    Otherwise, the file details are collected and a File instance is created.

    Args:
        file_location (str): The full path to the file.
        run_id (str): The ID of the run.
        data_collection (DataCollection): The data collection configuration.
        existing_files (List[dict]): Existing files from the database.
        update_files (bool): Whether to update existing file entries.
        full_regex (str): The regex pattern to match the filename.
        skip_regex (bool): Whether to skip the regex check.

    Returns:
        Optional[File]: A File instance if the file is valid; otherwise, None.
    """
    file_name = os.path.basename(file_location)
    if not skip_regex:
        if full_regex is None:
            raise ValueError("full_regex must be provided unless skip_regex is True")
        match, _ = regex_match(file_name, full_regex)
        if not match:
            # logger.debug(f"File {file_name} does not match regex, skipping.")
            return None

    # file_name = os.path.basename(file_location)
    # match, _ = regex_match(file_name, full_regex)
    # if not match:
    #     logger.debug(f"File {file_name} does not match regex, skipping.")
    #     return None

    # Check if the file already exists in the database.
    if existing_files:
        logger.debug(f"Existing Files: {existing_files}")
        if any(existing == file_location for existing in list(existing_files.keys())):
            logger.debug(f"File {file_name} already exists in the database.")
            if not update_files:
                logger.debug(f"Skipping existing file {file_name}.")
                return None
            logger.debug(f"Updating file {file_name}...")

    # Get file details.
    creation_time_float = os.path.getctime(file_location)
    modification_time_float = os.path.getmtime(file_location)
    creation_time_iso = format_timestamp(creation_time_float)
    modification_time_iso = format_timestamp(modification_time_float)
    filesize = os.path.getsize(file_location)
    file_hash = generate_file_hash(file_name, filesize, creation_time_iso, modification_time_iso)
    logger.debug(f"File Hash for {file_name}: {file_hash}")

    # Create the File instance.
    file_instance = File(
        filename=file_name,
        file_location=file_location,
        creation_time=creation_time_iso,
        modification_time=modification_time_iso,
        file_hash=file_hash,
        filesize=filesize,
        data_collection_id=data_collection.id,
        run_id=run_id,
    )
    logger.debug(f"File Instance: {file_instance}")
    return file_instance


@typechecked
def scan_run(
    run_location: str,
    run_tag: str,
    workflow_config: WorkflowConfig,
    data_collection: DataCollection,
    workflow_id: ObjectId,
    reprocess_runs: bool = False,
    update_files: bool = False,
    dbmanager: Optional[DBManager] = None,
) -> Union[WorkflowRun, None]:
    """
    Scan a single run folder (a directory containing result files and/or subfolders)
    and update the local TinyDB.

    Args:
        run_location (str): The directory of the run.
        run_tag (str): A tag/name for this run.
        workflow_config (WorkflowConfig): The workflow configuration object.
        data_collection (DataCollection): The data collection configuration object.
        workflow_id (ObjectId): The ID of the workflow.
        reprocess_runs (bool): Whether to reprocess the runs.
        update_files (bool): Whether to update file information.
        dbmanager (DBManager, optional): An instance of DBManager. One is created if not provided.

    Returns:
        WorkflowRun: The scanned workflow run.
    """
    if dbmanager is None:
        dbmanager = DBManager()

    if not os.path.exists(run_location):
        raise ValueError(f"The directory '{run_location}' does not exist.")
    if not os.path.isdir(run_location):
        raise ValueError(f"'{run_location}' is not a directory.")

    creation_time = format_timestamp(os.path.getctime(run_location))
    last_modification_time = format_timestamp(os.path.getmtime(run_location))

    # Check if the run already exists in the database
    existing_run = dbmanager.get_run_by_location(run_location)
    logger.debug(f"Existing Run: {existing_run}")
    if existing_run:
        logger.debug(f"Run {run_tag} already exists in the database.")
        if reprocess_runs:
            logger.info(f"Reprocessing run {run_tag}...")
            existing_run["id"] = PyObjectId(existing_run["id"])
            existing_run["workflow_config_id"] = PyObjectId(existing_run["workflow_config_id"])
            existing_run["workflow_id"] = PyObjectId(existing_run["workflow_id"])
            # existing_run["creation_time"] = creation_time
            # existing_run["last_modification_time"] = last_modification_time
            # existing_run.pop("execution_time", None)
            logger.debug(f"Existing Run: {existing_run}")
            workflow_run = WorkflowRun.from_mongo(existing_run)
            logger.debug(f"Workflow Run: {workflow_run}")
            logger.debug(f"Test Run: {WorkflowRun(**existing_run)}")
            existing_files = dbmanager.get_files_by_run(run_id=workflow_run.id)
            logger.debug(f"Existing Files: {existing_files}")
            existing_files_reformated = {e["file_location"]: e for e in existing_files}

        else:
            logger.info(f"Skipping existing run {run_tag}.")
            return  # or you could choose to return None
    else:
        workflow_run = WorkflowRun(
            workflow_id=workflow_id,
            run_tag=run_tag,
            files_id=[],
            workflow_config_id=workflow_config.id,
            run_location=run_location,
            creation_time=creation_time,
            last_modification_time=last_modification_time,
            hash="",
        )
        existing_files_reformated = []

    # Scan files in this run folder
    files = process_files(
        path=run_location,
        run_id=workflow_run.id,
        data_collection=data_collection,
        existing_files=existing_files_reformated,
        update_files=update_files,
    )

    old_updated_files = [file for file in files if str(file.file_location) in existing_files_reformated]

    new_files = [file for file in files if str(file.file_location) not in existing_files_reformated]

    rich_print_checked_statement(f"Number of scanned files in run {run_tag}: {len(files)} including {len(old_updated_files)} updated files and {len(new_files)} new files.", "info")

    # Upsert the files into the local database
    dbmanager.upsert_files_batch([file.tinydb() for file in files], update=update_files)
    workflow_run.files_id = [file.id for file in files]

    if not update_files and existing_run:
        files = [File.from_mongo(v) for k, v in existing_files_reformated.items()]

    # Generate the hash for the run
    run_hash = generate_run_hash(run_location, creation_time, last_modification_time, files)
    logger.debug(f"Run hash: {run_hash}")

    if workflow_run.hash != "":
        logger.debug(f"Existing run hash: {workflow_run.hash}")
        if reprocess_runs:
            differences = check_run_differences(workflow_run, run_location, creation_time, last_modification_time, files)
            logger.debug(f"Differences: {differences}")
            # rich_print_checked_statement(f"Reprocessing run {run_tag}...", "info")

        elif not reprocess_runs:
            if workflow_run.hash != run_hash:
                logger.warning(f"Hash mismatch for run {run_tag}.")
                differences = check_run_differences(workflow_run, run_location, creation_time, last_modification_time, files)
                logger.debug(f"Differences: {differences}")
                rich_print_checked_statement(
                    f"Hash mismatch for run {run_tag}. The run content has changed since the last scan. Please use --reprocess-runs to update the run content or check the logs for more details.",
                    "error",
                    exit=True,
                )
            else:
                logger.debug(f"Hash match for run {run_tag}.")
                # rich_print_checked_statement(f"Hash match for run {run_tag}.", "success")

    workflow_run.hash = run_hash
    # Upsert the workflow run into the local database
    dbmanager.upsert_runs_batch([workflow_run.tinydb()], update=reprocess_runs)

    return workflow_run


@typechecked
def scan_parent_folder(
    parent_runs_location: str,
    workflow_config: WorkflowConfig,
    data_collection: DataCollection,
    data_location: WorkflowDataLocation,
    workflow_id: ObjectId,
    structure: str = "sequencing-runs",  # or "direct-folder"
    reprocess_runs: bool = False,
    update_files: bool = False,
) -> List[Union[WorkflowRun, None]]:
    """
    Scan a parent folder either as multiple runs (each subdirectory is a run) or as a direct folder (the
    provided directory is a single run).

    Args:
        parent_runs_location (str): The parent directory containing the runs or files.
        workflow_config (WorkflowConfig): The workflow configuration object.
        data_collection (DataCollection): The data collection configuration object.
        data_location (WorkflowDataLocation): The data location configuration object.
        workflow_id (ObjectId): The ID of the workflow.
        structure (str): "sequencing-runs" to scan subdirectories, "direct-folder" to scan the folder itself.
        reprocess_runs (bool): Whether to reprocess the runs.
        update_files (bool): Whether to update file information.

    Returns:
        List[WorkflowRun]: A list of scanned WorkflowRun objects.
    """
    runs = list()
    dbmanager = DBManager()

    if not os.path.exists(parent_runs_location):
        raise ValueError(f"The directory '{parent_runs_location}' does not exist.")
    if not os.path.isdir(parent_runs_location):
        raise ValueError(f"'{parent_runs_location}' is not a directory.")

    if structure == "direct-folder":
        # Treat the provided directory as a single run
        run_tag = os.path.basename(os.path.normpath(parent_runs_location))
        workflow_run = scan_run(
            run_location=parent_runs_location,
            run_tag=run_tag,
            workflow_config=workflow_config,
            data_collection=data_collection,
            workflow_id=workflow_id,
            reprocess_runs=reprocess_runs,
            update_files=update_files,
            dbmanager=dbmanager,
        )
        runs.append(workflow_run)
    elif structure == "sequencing-runs":
        # Each subdirectory that matches the regex is a run
        for run in sorted(os.listdir(parent_runs_location)):
            run_path = os.path.join(parent_runs_location, run)
            if os.path.isdir(run_path) and re.match(data_location.runs_regex, run):
                workflow_run = scan_run(
                    run_location=run_path,
                    run_tag=run,
                    workflow_config=workflow_config,
                    data_collection=data_collection,
                    workflow_id=workflow_id,
                    reprocess_runs=reprocess_runs,
                    update_files=update_files,
                    dbmanager=dbmanager,
                )
                runs.append(workflow_run)
    else:
        raise ValueError(f"Unknown structure '{structure}'. Valid options are 'sequencing-runs' and 'direct-folder'.")

    return runs


@typechecked
def scan_files_for_data_collection(
    workflow: Workflow,
    data_collection_id: str,
    reprocess_runs: bool = False,
    update_files: bool = False,
) -> None:
    """
    Scan files for a given data collection of a workflow and track progress in the local TinyDB.

    Args:
        workflow (Workflow): The workflow configuration object.
        data_collection_id (str): The ID of the data collection to scan.
        data_collection_metatype (str): The metatype of the data collection.
        reprocess_runs (bool): Whether to reprocess the runs (default is False).
        update_files (bool): Whether to update the files (default is False).
    """
    workflow_id = workflow.id

    # Retrieve workflow and data collection details
    logger.debug("Fetching workflow and data collection details from local configurations...")

    data_collection = next((dc for dc in workflow.data_collections if str(dc.id) == data_collection_id), None)
    if not data_collection:
        logger.error(f"Data collection {data_collection_id} not found in workflow {workflow.workflow_tag}.")
        rich_print_checked_statement(f"Data collection {data_collection_id} not found in workflow {workflow.workflow_tag}.", "error")

    # Retrieve locations from the workflow config
    locations = workflow.data_location.locations

    # For a single-file scan (e.g. metadata), use the provided filename.
    if data_collection.config.scan.mode.lower() == "single":
        file_path = data_collection.config.scan.scan_parameters.filename
        logger.info(f"Scanning single file for data collection {data_collection.data_collection_tag}: {file_path}")

        # Check for the file's existence in the DB
        existing_file = DBManager().get_file_by_location(file_path)
        if existing_file:
            logger.debug(f"File {file_path} already exists in the database.")
        existing_files = {existing_file["file_location"]: existing_file} if existing_file else {}
        logger.debug(f"Existing Files: {existing_files}")

        # For single file mode we bypass regex matching.
        files = process_files(
            path=file_path,
            run_id=None,  # Use a fixed run id or generate one as appropriate
            data_collection=data_collection,
            existing_files=existing_files,  # Optionally load existing file records if needed
            update_files=update_files,
            skip_regex=True,
        )
        logger.debug(f"Scanned file(s): {files}")

        # Upsert the files into the local database
        dbmanager = DBManager()

        dbmanager.upsert_files_batch([file.tinydb() for file in files], update=update_files)
        rich_print_checked_statement(f"Scanned {len(files)} file(s) for data collection {data_collection.data_collection_tag}", "success")
    else:
        # For aggregate mode, use the existing parent folder scanning.
        locations = workflow.data_location.locations
        if not locations:
            rich_print_checked_statement(f"No locations configured for workflow {workflow.workflow_tag}.", "warning")
            return

        for location in locations:
            logger.info(f"Scanning location: {location}")
            runs_and_content = scan_parent_folder(
                parent_runs_location=location,
                workflow_config=workflow.config,
                data_location=workflow.data_location,
                data_collection=data_collection,
                workflow_id=workflow_id,
                structure=workflow.data_location.structure,
                reprocess_runs=reprocess_runs,
                update_files=update_files,
            )
            logger.debug(f"Runs and content: {runs_and_content}")
            rich_print_checked_statement(f"Scanned {len(runs_and_content)} runs in location {location}", "success")
