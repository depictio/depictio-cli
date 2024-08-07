import sys
from depictio_cli.models import AgentConfig
import os, yaml, typer, httpx
from typing import Dict, Optional, Tuple, List
from pydantic import BaseModel, validator
from depictio_cli.logging import logger


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


def load_depictio_config(config_path="~/.depictio/agent.yaml"):
    """
    Load the Depict.io configuration file.
    """
    try:
        with open(os.path.expanduser(config_path), "r") as f:
            config = yaml.safe_load(f)
            config = validate_depictio_agent_config(config)
            return config
    except FileNotFoundError:
        typer.echo("Depict.io configuration file not found. Please create a new user and generate a token.")
        raise typer.Exit(code=1)


def validate_depictio_agent_config(depictio_agent_config):
    # Validate the Depictio agent configuration
    config = AgentConfig(**depictio_agent_config)
    logger.info(f"Depictio agent configuration validated: {config}")

    return config.dict()


def login(config_path: str = "~/.depictio/agent.yaml"):
    depictio_agent_config = load_depictio_config(config_path=config_path)
    typer.echo(f"Depict.io agent configuration loaded: {depictio_agent_config}")

    # Connect to depictio API
    response = httpx.post(f"{depictio_agent_config['api_base_url']}/depictio/api/v1/cli/validate_agent_config", json=depictio_agent_config)
    if response.status_code == 200:
        typer.echo("Agent configuration is valid.")
        return {"success": True, "agent_config": depictio_agent_config}
    else:
        typer.echo(f"Agent configuration is invalid: {response.text}")
        return {"success": False}


def remote_validate_pipeline_config(agent_config: dict, pipeline_config_path: str):
    # Load the pipeline configuration
    pipeline_config = get_config(pipeline_config_path)

    # Validate that the pipeline config is correct using agent config and pipeline config
    logger.info(f"Agent config: {agent_config}")
    logger.info(f"Pipeline config: {pipeline_config}")

    token = agent_config["user"]["token"]["access_token"]

    response = httpx.post(f"{agent_config['api_base_url']}/depictio/api/v1/cli/validate_pipeline_config", json=pipeline_config, headers={"Authorization": f"Bearer {token}"})
    if response.status_code == 200:
        typer.echo("Pipeline configuration is valid.")
        return {"success": True, "config": pipeline_config}
    else:
        typer.echo(f"Pipeline configuration is invalid: {response.text}")
        return {"success": False, "config": pipeline_config}


def send_workflow_request(agent_config: dict, endpoint: str, workflow_data_dict: dict, headers: dict) -> None:
    """
    Send a request to the workflow API to create, update, or delete a workflow, based on the specified method.
    """
    print("Workflow data dict: ", workflow_data_dict)
    method_dict = {
        "create": "post",
        "update": "put",
        "delete": "delete",
    }
    method = method_dict[endpoint]

    # Dynamically select the HTTP method
    # Simplify by directly using the httpx.request method
    request_method = method.upper()  # Ensure method is in uppercase
    url = f"{agent_config['api_base_url']}/depictio/api/v1/workflows/{endpoint}"
    json_body = None if request_method == "DELETE" else workflow_data_dict

    response = httpx.request(
        method=request_method,
        url=url,
        headers=headers,
        json=json_body,
        timeout=30.0,
    )
    # print(response.json() if response.status_code != 204 else "")

    typer.echo(f"Response status code: {response.status_code}")
    typer.echo(f"Response text: {response.text}")

    # Check response status
    if response.status_code in [200, 204]:  # 204 for successful DELETE requests
        typer.echo(f"Workflow {workflow_data_dict.get('workflow_tag', 'N/A')} successfully {endpoint}d! : {response.json() if response.status_code != 204 else ''}")
        return response.json() if response.status_code != 204 else None
    else:
        typer.echo(f"Error during {endpoint}d: {response.text}")
        raise httpx.HTTPStatusError(message=f"Error during {endpoint}d: {response.text}", request=response.request, response=response)


def check_workflow_exists(agent_config: dict, workflow_dict: dict, headers: dict) -> Tuple[bool, Optional[Dict]]:
    """
    Check if the workflow exists and return its details if it does.
    """

    workflow_tag = f"{workflow_dict['engine']}/{workflow_dict['name']}"
    response = httpx.get(
        f"{agent_config['api_base_url']}/depictio/api/v1/workflows/get?workflow_tag={workflow_tag}",
        headers=headers,
        timeout=30.0,
    )
    if response.status_code == 200:
        return True, response.json()
    return False, None


def compare_models(agent_config: dict, new_workflow: dict, existing_workflow: dict, headers: dict) -> bool:
    """
    Compare the models of two workflows.
    """
    # Check if the workflow exists
    if not existing_workflow:
        return {"exists": False, "match": False, "message": "Empty existing workflow."}
    if not new_workflow:
        return {"exists": True, "match": False, "message": "Empty new workflow."}
    response = httpx.post(
        f"{agent_config['api_base_url']}/depictio/api/v1/workflows/compare_workflow_models",
        json={"new_workflow": new_workflow, "existing_workflow": existing_workflow},
        headers=headers,
    )
    if response.status_code == 200:
        return {"exists": True, "match": response.json()["match"], "message": response.json()["message"]}

    else:
        return {"exists": True, "match": False, "message": response.text}


def create_update_delete_workflow(
    agent_config: dict,
    workflow_data_dict: dict,
    headers: dict,
    update: bool = False,
) -> None:
    """
    Create or update a workflow based on the update flag.
    """

    endpoint = "update" if update else "create"



    exists, _ = check_workflow_exists(agent_config, workflow_data_dict, headers)

    typer.echo(f"Workflow {exists}")

    # Check if the workflow exists
    if exists:
        # If the workflow exists, check if there is a conflict with the existing workflow
        check_modif = compare_models(agent_config, workflow_data_dict, _, headers)

        typer.echo(f"Workflow {workflow_data_dict['workflow_tag']} has a conflict: {check_modif}")

        # If the workflow exists but there is a conflict, check if the user wants to update the existing workflow
        if not check_modif:
            # If the user does not want to update the existing workflow, exit
            if not update:
                sys.exit(
                    f"Workflow {workflow_data_dict['workflow_tag']} already exists but with different configuration. Please use the --update flag to update the existing workflow."
                )

            # If the user wants to update the existing workflow, update it
            else:
                typer.echo(f"Workflow {workflow_data_dict['workflow_tag']} already exists, updating it.")
                return send_workflow_request(agent_config, endpoint, workflow_data_dict, headers)

        # If the workflow exists and there is no conflict, skip the creation
        else:
            typer.echo(f"Workflow {workflow_data_dict['workflow_tag']} already exists, skipping creation.")
            return_dict = {str(_["_id"]): [str(data_collection["_id"]) for data_collection in _["data_collections"]]}
            return return_dict

    # If the workflow does not exist, create it
    typer.echo(f"Workflow {workflow_data_dict['name']} does not exist, creating it.")
    workflow_json = send_workflow_request(agent_config, endpoint, workflow_data_dict, headers)
    return workflow_json


# TODO: change logic to just initiate the scan and not wait for the completion (thousands of files can take a long time)
def scan_files_for_data_collection(agent_config: dict, workflow_id: str, data_collection_id: str, headers: dict, scan_type: str = "scan") -> None:
    """
    Scan files for a given data collection of a workflow.
    """

    response = httpx.post(
        f"{agent_config['api_base_url']}/depictio/api/v1/files/{scan_type}/{workflow_id}/{data_collection_id}",
        headers=headers,
        timeout=5 * 60,  # Increase the timeout as needed
    )
    if response.status_code == 200:
        typer.echo(f"Files successfully scanned for data collection {data_collection_id}!")
    else:
        typer.echo(f"Error for data collection {data_collection_id}: {response.text}")


def create_deltatable_request(agent_config: dict, workflow_id: str, data_collection_id: str, headers: dict) -> None:
    """
    Create a delta table for a given data collection of a workflow.
    """
    response = httpx.post(
        f"{agent_config['api_base_url']}/depictio/api/v1/deltatables/create/{workflow_id}/{data_collection_id}",
        headers=headers,
        timeout=60.0 * 5,  # Increase the timeout as needed
    )
    if response.status_code == 200:
        typer.echo(f"Data successfully aggregated for data collection {data_collection_id}!")
    else:
        typer.echo(f"Error for data collection {data_collection_id}: {response.text}")


def create_trackset(agent_config: dict, workflow_id: str, data_collection_id: str, headers: dict) -> None:
    """
    Upload the trackset to S3 for a given data collection of a workflow.
    """
    print("creating trackset")
    print("workflow_id", workflow_id)
    print("data_collection_id", data_collection_id)
    response = httpx.post(
        f"{agent_config['api_base_url']}/depictio/api/v1/jbrowse/create_trackset/{workflow_id}/{data_collection_id}",
        headers=headers,
        timeout=60.0 * 5,  # Increase the timeout as needed
    )
    if response.status_code == 200:
        typer.echo(f"Trackset successfully created for data collection {data_collection_id}!")
    else:
        typer.echo(f"Error for data collection {data_collection_id}: {response.text}")

    return response
