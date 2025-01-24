import json
from pathlib import Path
from depictio_cli.logging import logger

METADATA_FILE = Path.home() / ".depictio/projects_metadata.json"


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


