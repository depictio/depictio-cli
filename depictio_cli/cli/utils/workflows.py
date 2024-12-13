
import json
import sys
from depictio_cli.cli.utils.data_collections import process_data_collection_helper
import os, yaml, typer, httpx
from typing import Dict, Optional, Tuple, List
from depictio_cli.logging import logger

def send_workflow_request(cli_config: dict, endpoint: str, workflow_data_dict: dict, headers: dict) -> None:
    """
    Send a request to the workflow API to create, update, or delete a workflow, based on the specified method.
    """
    # logger.info("Workflow data dict: ", workflow_data_dict)
    method_dict = {
        "create": "post",
        "update": "put",
        "delete": "delete",
    }
    method = method_dict[endpoint]

    # Dynamically select the HTTP method
    # Simplify by directly using the httpx.request method
    request_method = method.upper()  # Ensure method is in uppercase
    url = f"{cli_config['api_base_url']}/depictio/api/v1/workflows/{endpoint}"
    json_body = None if request_method == "DELETE" else workflow_data_dict

    response = httpx.request(
        method=request_method,
        url=url,
        headers=headers,
        json=json_body,
        timeout=30.0,
    )
    # logger.info(response.json() if response.status_code != 204 else "")

    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response text: {response.text}")

    # Check response status
    if response.status_code in [200, 204]:  # 204 for successful DELETE requests
        logger.info(f"Workflow {workflow_data_dict.get('workflow_tag', 'N/A')} successfully {endpoint}d! : {response.json() if response.status_code != 204 else ''}")
        return response.json() if response.status_code != 204 else None
    else:
        logger.error(f"Error during {endpoint}d: {response.text}")
        raise httpx.HTTPStatusError(message=f"Error during {endpoint}d: {response.text}", request=response.request, response=response)


def check_workflow_exists(api_url: str, workflow_dict: dict, headers: dict) -> Tuple[bool, Optional[Dict]]:
    """
    Check if the workflow exists and return its details if it does.
    """
    response = httpx.get(
        f"{api_url}/depictio/api/v1/workflows/get/from_args",
        params={"name": workflow_dict["name"], "engine": workflow_dict["engine"]},
        headers=headers,
        timeout=30.0,
    )
    if response.status_code == 200:
        return True, response.json()
    return False, None


def compare_models(cli_config: dict, new_workflow: dict, existing_workflow: dict, headers: dict) -> bool:
    """
    Compare the models of two workflows.
    """

    logger.debug(f"Existing workflow: {existing_workflow}")
    logger.debug(f"New workflow: {new_workflow}")

    # Check if the workflow exists
    if not existing_workflow:
        return {"exists": False, "match": False, "message": "Empty existing workflow."}
    if not new_workflow:
        return {"exists": True, "match": False, "message": "Empty new workflow."}
    response = httpx.post(
        f"{cli_config['api_base_url']}/depictio/api/v1/workflows/compare_workflow_models",
        json={"new_workflow": new_workflow, "existing_workflow": existing_workflow},
        headers=headers,
    )
    if response.status_code == 200:
        return {"exists": True, "match": response.json()["match"], "message": response.json()["message"]}

    else:
        return {"exists": True, "match": False, "message": response.text}


def create_update_delete_workflow(
    project_config: dict,
    workflow_data_dict: dict,
    headers: dict,
    cli_config : dict,
    update: bool = False,
) -> None:
    """
    Create or update a workflow based on the update flag.
    """
    logger.debug(f"Workflow data dict: {workflow_data_dict}")

    endpoint = "update" if update else "create"

    exists, _ = check_workflow_exists(cli_config["api_base_url"], workflow_data_dict, headers)

    logger.debug(f"Workflow {exists}")
    logger.debug(f"Update: {update}")

    logger.debug(f"Endpoint: {endpoint}")
    logger.debug(f"Agent config: {cli_config}")

    logger.debug(f"Headers: {headers}")
    logger.debug(f"_ : {_}")
    typer.Exit(code=1)

    # Check if the workflow exists
    if exists:
        # If the workflow exists, check if there is a conflict with the existing workflow
        logger.debug(f"Existing workflow: {_}")
        logger.debug(f"New workflow: {workflow_data_dict}")

        check_modif = compare_models(cli_config, workflow_data_dict, _, headers)

        logger.debug(f"Check modification: {check_modif}")
        typer.Exit(code=1)

        # If the workflow exists but there is a conflict, check if the user wants to update the existing workflow
        if not check_modif:
            # If the user does not want to update the existing workflow, exit
            if not update:
                sys.exit(
                    f"Workflow {workflow_data_dict['workflow_tag']} already exists but with different configuration. Please use the --update flag to update the existing workflow."
                )

            # If the user wants to update the existing workflow, update it
            else:
                logger.info(f"Workflow {workflow_data_dict['workflow_tag']} already exists, updating it.")
                return send_workflow_request(cli_config, endpoint, workflow_data_dict, headers)

        # If the workflow exists and there is no conflict, skip the creation
        else:
            if check_modif["match"]:

                logger.warning(f"Workflow {workflow_data_dict['workflow_tag']} already exists, skipping creation.")
                # return_dict = {str(_["_id"]): [str(data_collection["_id"]) for data_collection in _["data_collections"]]}
                # logger.info(f"Return dict: {return_dict}")
                # return return_dict

                return _
            else:
                if not update:
                    sys.exit(
                        f"Workflow {workflow_data_dict['workflow_tag']} already exists but with different configuration. Please use the --update flag to update the existing workflow."
                    )
                else:
                    logger.info(f"Workflow {workflow_data_dict['workflow_tag']} already exists, updating it.")
                    return send_workflow_request(cli_config, endpoint, workflow_data_dict, headers)

    # If the workflow does not exist, create it
    logger.info(f"Workflow {workflow_data_dict['name']} does not exist, creating it.")
    logger.info(f"Endpoint: {endpoint}")
    workflow_json = send_workflow_request(cli_config, endpoint, workflow_data_dict, headers)
    return workflow_json



def process_workflow_helper(cli_config, wf, headers, scan_files=True, data_collection_tag=None):
    logger.info(f"Processing Workflow: {wf['name']}")
    wf_id = str(wf["_id"])
    for dc in wf["data_collections"]:
        logger.info(f"Processing Data collection: {dc['data_collection_tag']}")
        if data_collection_tag:
            logger.info(f"Data collection tag: {data_collection_tag}")
            if dc["data_collection_tag"].lower() == data_collection_tag.lower():
                process_data_collection_helper(cli_config, wf_id, dc, headers)
        else:
            process_data_collection_helper(cli_config, wf_id, dc, headers)
