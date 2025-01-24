import os
import typer
import yaml
from typeguard import typechecked

from depictio_cli.cli.utils.rich_utils import handle_error
from depictio_cli.logging import logger
from depictio_models.models.cli import CLIConfig
from depictio_models.utils import convert_model_to_dict

@typechecked
def generate_api_headers(CLI_config: dict) -> dict:
    """
    Generate the API headers.
    """
    if not CLI_config:
        raise ValueError("CLI_config is required.")
    
    if isinstance(CLI_config, CLIConfig):
        CLI_config = CLI_config.model_dump()
    elif not isinstance(CLI_config, dict):
        raise TypeError(f"project_config must be a dictionary, got {type(CLI_config)}")


    # Get the token from the CLI configuration
    token = CLI_config["user"]["token"]["access_token"]

    return {"Authorization": f"Bearer {token}"}


@typechecked
def get_config(filename: str) -> dict:
    """
    Get the config file.
    """
    if not filename.endswith(".yaml"):
        # raise ValueError("Invalid config file. Please check your filename. Must be a valid YAML file.")
        handle_error(f"Invalid config file : {filename}. Please check your filename. Must be a valid YAML file.", exit=True)
    if not os.path.exists(filename):
        # raise ValueError(f"The file '{filename}' does not exist.")
        handle_error(f"The file '{filename}' does not exist.", exit=True)
    if not os.path.isfile(filename):
        # raise ValueError(f"'{filename}' is not a file.")
        handle_error(f"'{filename}' is not a file.", exit=True)
    else:
        with open(filename, "r") as f:
            yaml_data = yaml.safe_load(f)
        return yaml_data

@typechecked
def validate_depictio_cli_config(depictio_cli_config: dict) -> dict:
    """
    Validate the Depictio CLI configuration.
    """
    # Validate the Depictio CLI configuration
    from depictio_models.models.cli import CLIConfig

    config = CLIConfig(**depictio_cli_config)
    logger.info(f"Depictio CLI configuration validated: {config}")
    config = convert_model_to_dict(config)

    return config


@typechecked
def load_depictio_config(yaml_config_path : str = "~/.depictio/cli.yaml") -> dict:
    """
    Load the Depictio configuration file.
    """
    try:
        from depictio_cli.cli.utils.rich_utils import rich_print_checked_statement
        rich_print_checked_statement("Loading Depictio configuration...", "loading")
        config = get_config(os.path.expanduser(yaml_config_path))
        config = validate_depictio_cli_config(config)
        return config
    except FileNotFoundError:
        logger.error("Depictio configuration file not found. Please create a new user and generate a token.")
        raise typer.Exit(code=1)
