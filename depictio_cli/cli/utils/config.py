
import json
import sys
import os, yaml, typer, httpx
from typing import Dict, Optional, Tuple, List
from depictio_cli.logging import logger

def validate_and_prepare(
    CLI_config_path: str,
    project_config_path: str
) -> tuple[dict, dict]:
    """
    Validate the CLI and pipeline configurations, and prepare headers for API requests.

    Args:
        CLI_config_path (str): Path to the CLI configuration file.
        project_config_path (str): Path to the pipeline configuration file.

    Returns:
        tuple: A tuple containing the validated configuration and headers.
    
    Raises:
        typer.Exit: If validation or login fails.
    """
    # Authenticate the CLI
    login_response = login(CLI_config_path)
    logger.debug(f"login_response: {login_response}")

    if not login_response["success"]:
        logger.error("Login failed.")
        raise typer.Exit(code=1)

    # Validate the pipeline configuration
    response = remote_validate_project_config(login_response["CLI_config"], project_config_path)

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


def load_depictio_config(config_path="~/.depictio/agent.yaml"):
    """
    Load the Depictio configuration file.
    """
    try:
        with open(os.path.expanduser(config_path), "r") as f:
            config = yaml.safe_load(f)
            config = validate_depictio_cli_config(config)
            return config
    except FileNotFoundError:
        logger.error("Depictio configuration file not found. Please create a new user and generate a token.")
        raise typer.Exit(code=1)


def validate_depictio_cli_config(depictio_cli_config):
    # Validate the Depictio CLI configuration
    from depictio_models.models.cli import CLIConfig
    config = CLIConfig(**depictio_cli_config)
    logger.info(f"Depictio CLI configuration validated: {config}")

    return config.dict()


def login(config_path: str = "~/.depictio/agent.yaml"):
    depictio_CLI_config = load_depictio_config(config_path=config_path)
    logger.info(f"Depictio CLI configuration loaded: {depictio_CLI_config}")

    # Connect to depictio API
    response = httpx.post(f"{depictio_CLI_config['api_base_url']}/depictio/api/v1/cli/validate_cli_config", json=depictio_CLI_config)
    if response.status_code == 200:
        logger.info("Agent configuration is valid.")
        return {"success": True, "CLI_config": depictio_CLI_config}
    else:
        logger.error(f"Agent configuration is invalid: {response.text}")
        return {"success": False}


def remote_validate_project_config(CLI_config: dict, project_config_path: str):
    # Load the pipeline configuration
    pipeline_config = get_config(project_config_path)

    # Validate that the pipeline config is correct using CLI config and pipeline config
    logger.debug(f"CLI config: {CLI_config}")
    logger.debug(f"Project config: {pipeline_config}")

    token = CLI_config["user"]["token"]["access_token"]

    try:
        logger.info("Validating pipeline configuration...")
        logger.debug(f"Token: {token}")
        response = httpx.post(f"{CLI_config['api_base_url']}/depictio/api/v1/cli/validate_project_config", json=pipeline_config, headers={"Authorization": f"Bearer {token}"})
        # Log the response status, headers, and content
        logger.debug(f"Status code: {response.status_code}")
        logger.debug(f"Response Headers: {response.headers}")
        logger.debug(f"Response Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
        logger.debug(f"Response Text: {response.text}")
        logger.debug(f"Token: {token}")
        logger.debug(f"Pipeline config: {pipeline_config}")

        # Attempt to parse the response JSON if the status is 200
        if response.status_code == 200:
            response_json = response.json()
            logger.debug(f"Response JSON: {json.dumps(response_json, indent=2)}")
            return {"success": True, "config": response_json.get("config", {})}
        else:
            logger.error("Failed to validate the pipeline configuration.")
            return {"success": False}
    except httpx.RequestError as e:
        logger.error(f"Request error occurred: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding failed: {e}")
        logger.error(f"Raw Response Content: {response.text if response else 'No response'}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

    return {"success": False}
