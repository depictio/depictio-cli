import collections
import hashlib
import json
from pathlib import Path
import sys
import os, yaml, typer, httpx
from typing import Dict, Optional, Tuple, List
from depictio_cli.logging import logger
from depictio_models.utils import validate_model_config
from depictio_models.models.projects import Project
from depictio_models.models.base import convert_objectid_to_str


# metadata_keys.py (or within the same module as local_validate_project_config)

METADATA_FILE = Path.home() / ".depictio/projects_metadata.json"


KEYS_TO_SAVE = {
    "id": None,
    "name": None,
    "hash": None,
    "yaml_config_path": None,
    "permissions": {
        "owners": [{"id": None}],
        "editors": [{"id": None}],
        "viewers": [{"id": None}],
    },
    "workflows": [
        {
            "id": None,
            "name": None,
            "workflow_tag": None,
            "data_collections": [{"id": None, "data_collection_tag": None}],
        }
    ],
}


def login_and_validate_project_config(CLI_yaml_config_path: str, project_yaml_config_path: str) -> tuple[dict, dict]:
    """
    Validate the CLI and pipeline configurations, and prepare headers for API requests.

    Args:
        CLI_yaml_config_path (str): Path to the CLI configuration file.
        project_yaml_config_path (str): Path to the pipeline configuration file.

    Returns:
        tuple: A tuple containing the validated configuration and headers.

    Raises:
        typer.Exit: If validation or login fails.
    """
    # Authenticate the CLI
    login_response = login(CLI_yaml_config_path)
    logger.debug(f"login_response: {login_response}")

    if not login_response["success"]:
        logger.error("Login failed.")
        raise typer.Exit(code=1)

    # Validate the pipeline configuration
    response = local_validate_project_config(login_response["CLI_config"], project_yaml_config_path)
    logger.debug(f"response: {response}")
    # response = remote_validate_project_config(login_response["CLI_config"], project_yaml_config_path)

    if not response["success"]:
        logger.error("Pipeline configuration validation failed.")
        raise typer.Exit(code=1)

    logger.info("Pipeline configuration validated.")
    validated_config = response["config"]
    logger.debug(f"Validated config: {validated_config}")

    # Prepare headers
    headers = {"Authorization": f"Bearer {login_response['CLI_config']['user']['token']['access_token']}"}

    # Prepare API URL
    cli_config = login_response["CLI_config"]

    return validated_config, headers, cli_config


def get_config(filename: str):
    """
    Get the config file.
    """
    if not filename.endswith(".yaml"):
        raise ValueError("Invalid config file. Must be a YAML file.")
    if not os.path.exists(filename):
        raise ValueError(f"The file '{filename}' does not exist.")
    if not os.path.isfile(filename):
        raise ValueError(f"'{filename}' is not a file.")
    else:
        with open(filename, "r") as f:
            yaml_data = yaml.safe_load(f)
        return yaml_data


def load_depictio_config(yaml_config_path="~/.depictio/agent.yaml"):
    """
    Load the Depictio configuration file.
    """
    try:
        config = get_config(os.path.expanduser(yaml_config_path))
        config = validate_depictio_cli_config(config)
        return config
    except FileNotFoundError:
        logger.error("Depictio configuration file not found. Please create a new user and generate a token.")
        raise typer.Exit(code=1)


def validate_depictio_cli_config(depictio_cli_config) -> dict:
    # Validate the Depictio CLI configuration
    from depictio_models.models.cli import CLIConfig

    config = CLIConfig(**depictio_cli_config)
    logger.info(f"Depictio CLI configuration validated: {config}")

    return config.dict()


def login(yaml_config_path: str = "~/.depictio/agent.yaml"):
    depictio_CLI_config = load_depictio_config(yaml_config_path=yaml_config_path)
    logger.info(f"Depictio CLI configuration loaded: {depictio_CLI_config}")

    # Connect to depictio API
    response = httpx.post(f"{depictio_CLI_config['api_base_url']}/depictio/api/v1/cli/validate_cli_config", json=depictio_CLI_config)
    if response.status_code == 200:
        logger.info("Agent configuration is valid.")
        return {"success": True, "CLI_config": depictio_CLI_config}
    else:
        logger.error(f"Agent configuration is invalid: {response.text}")
        return {"success": False}


def merge_preserve_ids(existing, new):
    """
    Recursively merge two nested structures (dicts/lists), preserving ID fields from the existing structure.
    """
    logger.debug(f"Existing: {existing}")
    logger.debug(f"New: {new}")
    logger.debug(f"\n")
    if isinstance(existing, dict) and isinstance(new, dict):
        for key, new_value in new.items():
            logger.debug(f"Key: {key}, New Value: {new_value}")
            if key in existing:
                # Preserve the 'id' field if present
                if key == "id":
                    logger.debug(f"Preserving ID: {existing[key]}")
                    new[key] = existing[key]
                elif "id" in key:
                    logger.debug(f"DEBUG - Preserving ID: {existing[key]}")
                else:
                    new[key] = merge_preserve_ids(existing[key], new_value)
        return new

    elif isinstance(existing, list) and isinstance(new, list):
        # Create lookup dictionaries based on multiple potential unique keys
        def create_lookup(items, keys):
            lookup = {}
            for item in items:
                if isinstance(item, dict):
                    for k in keys:
                        if k in item:
                            # Map the unique key's value to the item
                            lookup[(k, item[k])] = item
            return lookup

        # Define which keys to consider for matching in order of priority
        unique_keys = ["id", "name", "workflow_tag", "data_collection_tag"]

        existing_lookup = create_lookup(existing, unique_keys)

        merged_list = []
        for new_item in new:
            logger.debug(f"New item: {new_item}")
            match = None
            if isinstance(new_item, dict):
                # Attempt to find a match based on each unique key
                for key in unique_keys:
                    logger.debug(f"Checking key: {key}")
                    if key in new_item and (key, new_item[key]) in existing_lookup:
                        match = existing_lookup[(key, new_item[key])]
                        logger.debug(f"Match found for key '{key}': {match}")
                        logger.debug(f"New item: {new_item}")
                        # If matching by a key other than 'id', transfer the existing 'id'
                        if key != "id" and "id" in match:
                            new_item["id"] = match["id"]
                        break

                if match:
                    merged_list.append(merge_preserve_ids(match, new_item))
                else:
                    merged_list.append(new_item)
            else:
                merged_list.append(new_item)
        return merged_list

    else:
        return new


def find_by_name(collection, name):
    """
    Search a list of dicts for an item with a matching 'name'.
    Returns the dict if found, otherwise None.
    """
    for item in collection:
        if isinstance(item, dict) and item.get("name") == name:
            return item
    return None


def find_matching_entry(collection, new_item):
    """
    Search a list of dicts for an item that matches new_item based on certain keys.
    Keys checked (in order): 'name', 'workflow_tag', 'data_collection_tag'.
    Returns the dict if a match is found, otherwise None.
    """
    for item in collection:
        if not isinstance(item, dict):
            continue
        # Check for match on 'name'
        if "name" in new_item and new_item["name"] == item.get("name"):
            return item
        # Check for match on 'workflow_tag'
        if "workflow_tag" in new_item and new_item["workflow_tag"] == item.get("workflow_tag"):
            return item
        # Check for match on 'data_collection_tag'
        if "data_collection_tag" in new_item and new_item["data_collection_tag"] == item.get("data_collection_tag"):
            return item
    return None


def assign_ids_by_keys(existing_meta, new_structure):
    """
    Recursively traverses new_structure. For each dict with identifying keys,
    attempts to find a matching dict in existing_meta to copy its 'id'.
    """
    if isinstance(new_structure, dict):
        match = find_matching_entry(existing_meta, new_structure)
        if match and "id" in match:
            new_structure["id"] = match["id"]

        # Recurse into nested dictionaries or lists
        for key, value in new_structure.items():
            if isinstance(value, (dict, list)):
                # Determine context for nested lists like workflows or data_collections
                if key in ["workflows", "data_collections"] and match:
                    nested_context = match.get(key, [])
                    new_structure[key] = assign_ids_by_keys(nested_context, value)
                else:
                    new_structure[key] = assign_ids_by_keys(existing_meta, value)

    elif isinstance(new_structure, list):
        for idx, item in enumerate(new_structure):
            new_structure[idx] = assign_ids_by_keys(existing_meta, item)

    return new_structure


def load_and_prepare_config(CLI_config: dict, project_yaml_config_path: str) -> dict:
    """
    Load the pipeline configuration, set the YAML config path, and add permissions.
    """
    # Load the pipeline configuration
    pipeline_config = get_config(project_yaml_config_path)
    full_path = os.path.abspath(project_yaml_config_path)
    pipeline_config["yaml_config_path"] = full_path

    # Add permissions based on the CLI user, removing 'token'
    user_light = CLI_config["user"].copy()
    user_light.pop("token", None)
    pipeline_config["permissions"] = {"owners": [user_light], "editors": [], "viewers": []}

    logger.debug(f"Pipeline config after adding permissions: {pipeline_config}")
    return pipeline_config


def merge_existing_ids(local_metadata: list, pipeline_config: dict) -> dict:
    """
    If a project with the same name exists, checks ownership and merges existing IDs.
    """
    # Assuming local_metadata is a list of project dicts
    project_name = pipeline_config["name"]
    existing_entry = next((entry for entry in local_metadata if entry["name"] == project_name), None)

    # Check if the project exists and is owned by the same user
    if existing_entry:
        user_id = pipeline_config["permissions"]["owners"][0]["id"]
        if existing_entry["permissions"]["owners"][0]["id"] != user_id:
            raise ValueError(f"Project '{project_name}' exists but is owned by a different user.")

        logger.info(f"Project owner is the same for '{project_name}' - Owner ID: {user_id}")
        logger.info(f"Project '{project_name}' exists with ID: {existing_entry['id']}")
        # Merge existing IDs using the provided function
        pipeline_config = assign_ids_by_keys(local_metadata, pipeline_config)
        logger.debug(f"Project config after merging IDs: {pipeline_config}")

    return pipeline_config


# Define nested keys to save
def extract_metadata(data, keys_structure):
    """Recursively extract metadata based on a keys structure."""
    if isinstance(keys_structure, dict):
        return {key: extract_metadata(data.get(key, {}), sub_keys) for key, sub_keys in keys_structure.items()}
    elif isinstance(keys_structure, list):
        return [extract_metadata(item, keys_structure[0]) for item in data] if isinstance(data, list) else []
    else:
        return data


def create_metadata_entry(validated_config, keys_to_save):
    """
    Convert validated configuration to a metadata entry, compute hash, and return the entry.
    """
    # Convert ObjectId to str if necessary and extract metadata
    config_dict = convert_objectid_to_str(validated_config.model_dump())
    metadata_entry = extract_metadata(config_dict, keys_to_save)

    # Compute hash for the metadata entry
    hash_value = hashlib.md5(json.dumps(metadata_entry, sort_keys=True).encode()).hexdigest()
    metadata_entry["hash"] = hash_value
    logger.debug(f"Metadata entry: {metadata_entry}")
    return metadata_entry


def local_validate_project_config(CLI_config: dict, project_yaml_config_path: str):
    try:
        logger.info("Validating pipeline configuration...")
        # Load and prepare the pipeline configuration
        pipeline_config = load_and_prepare_config(CLI_config, project_yaml_config_path)
        logger.debug(f"CLI config: {CLI_config}")
        logger.debug(f"Project config: {pipeline_config}")

        # Load existing metadata and merge IDs if necessary
        local_metadata = load_metadata()

        # Check if project already exists and merge IDs if necessary
        if pipeline_config["name"] in [entry["name"] for entry in local_metadata]:
            pipeline_config = merge_existing_ids(local_metadata, pipeline_config)

        # Validate configuration against the Project model
        validated_config = validate_model_config(pipeline_config, Project)
        logger.info(f"Pipeline configuration validated: {validated_config}")

        # Create metadata entry and update metadata
        metadata_entry = create_metadata_entry(validated_config, KEYS_TO_SAVE)
        update_metadata(metadata_entry)

        return {"success": True, "config": metadata_entry}

    except ValueError as e:
        logger.error(f"Pipeline configuration validation failed: {e}")
        return {"success": False}


def load_metadata() -> dict:
    """Load metadata from the sidecar JSON file."""
    if METADATA_FILE.exists():
        with open(METADATA_FILE, "r") as file:
            return json.load(file)
    return list()


def save_metadata(metadata: dict):
    """Save metadata to the sidecar JSON file."""
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Saving metadata to {METADATA_FILE}")
    with open(METADATA_FILE, "w") as file:

        json.dump(metadata, file, indent=4)


def compare_entries(existing_entry, new_entry, path=""):
    """
    Recursively compare two nested dictionaries or lists and identify differences.

    Args:
        existing_entry (dict or list): The existing entry.
        new_entry (dict or list): The new entry.
        path (str): The current path in the nested structure for better readability.

    Returns:
        dict: A dictionary detailing the differences.
    """
    differences = {}

    if isinstance(existing_entry, dict) and isinstance(new_entry, dict):
        # Compare keys in both dictionaries
        all_keys = set(existing_entry.keys()).union(set(new_entry.keys()))
        for key in all_keys:
            current_path = f"{path}.{key}" if path else key
            if key not in existing_entry:
                differences[current_path] = {"type": "missing_in_existing", "value": new_entry[key]}
            elif key not in new_entry:
                differences[current_path] = {"type": "missing_in_new", "value": existing_entry[key]}
            else:
                # Recurse into nested structures
                diff = compare_entries(existing_entry[key], new_entry[key], current_path)
                differences.update(diff)
    elif isinstance(existing_entry, list) and isinstance(new_entry, list):
        # Compare lists element by element
        max_len = max(len(existing_entry), len(new_entry))
        for index in range(max_len):
            current_path = f"{path}[{index}]"
            if index >= len(existing_entry):
                differences[current_path] = {"type": "missing_in_existing", "value": new_entry[index]}
            elif index >= len(new_entry):
                differences[current_path] = {"type": "missing_in_new", "value": existing_entry[index]}
            else:
                # Recurse into nested structures
                diff = compare_entries(existing_entry[index], new_entry[index], current_path)
                differences.update(diff)
    else:
        # Compare values directly
        if existing_entry != new_entry:
            differences[path] = {"type": "value_difference", "existing": existing_entry, "new": new_entry}

    return differences


def update_metadata(new_entry: dict):
    """
    Update the metadata for a project, adding or modifying the entry.

    Args:
        project_id (str): The unique ID for the project.
        name (str): The name of the project.
        yaml_config_path (str): The path to the project's configuration file.

    Raises:
        ValueError: If the metadata entry already exists and the name or yaml_config_path has changed.
    """
    logger.debug(f"New metadata entry: {new_entry}")

    metadata = load_metadata()
    metadata_ids = [entry["id"] for entry in metadata]
    logger.debug(f"Existing metadata: {metadata}")

    project_id = new_entry["id"]
    name = new_entry["name"]
    yaml_config_path = new_entry["yaml_config_path"]

    # Check if the project already exists
    if project_id in metadata_ids:
        logger.info(f"Metadata for project_id '{project_id}' already exists.")
        existing_entry = next(entry for entry in metadata if entry["id"] == project_id)

        # Compare hash values between existing and new entries
        if existing_entry["hash"] == new_entry["hash"]:
            logger.info(f"Metadata for project_id '{project_id}' already exists and is identical.")
            return

        else:
            logger.error(f"Metadata for project_id '{project_id}' already exists but is different.")

            differences = compare_entries(existing_entry, new_entry)
            logger.debug(f"Differences: {differences}")

            raise ValueError("Metadata entry already exists but the name or yaml_config_path has changed.")
    else:

        # Add or update the project entry
        metadata.append(new_entry)
        logger.info(f"New metadata entry added: {new_entry}")

    logger.info(f"Metadata updated: {metadata}")

    save_metadata(metadata)
    logger.info("Metadata saved.")
