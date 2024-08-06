from depictio_cli.models import AgentConfig
import os, yaml, typer, httpx
from depictio_cli.logging import logger


def load_depictio_config(config_path="~/.depictio/config.yaml"):
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
    response = httpx.post(f"{depictio_agent_config['api_base_url']}/depictio/api/v1/auth/validate_agent_config", json=depictio_agent_config)
    if response.status_code == 200:
        typer.echo("Agent configuration is valid.")
    else:
        typer.echo(f"Agent configuration is invalid: {response.text}")
