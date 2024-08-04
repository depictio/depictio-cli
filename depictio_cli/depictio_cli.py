import getpass
import json
import os
import sys

# from pprint import pprint
import httpx
import typer
from typing import Dict, Optional, Tuple, List
from pydantic import BaseModel, field_validator
from jose import JWTError
from devtools import debug
import yaml
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s - %(funcName)s - line %(lineno)d - %(message)s")
logger = logging.getLogger("depictio-cli")

app = typer.Typer()


class TokenData(BaseModel):
    access_token: str
    expire_datetime: str

    @field_validator("access_token")
    def validate_access_token(cls, v):
        if not v:
            raise ValueError("Access token cannot be empty")
        return v

    @field_validator("expire_datetime")
    def validate_expire_datetime(cls, v):
        if not v:
            raise ValueError("Expire datetime cannot be empty")
        else:
            try:
                if datetime.strptime(v, "%Y-%m-%d %H:%M:%S") < datetime.now():
                    raise ValueError("Token has expired")
            except ValueError:
                raise ValueError("Incorrect data format, should be YYYY-MM-DD HH:MM:SS")
        return v

class UserAgent(BaseModel):
    email: str
    token: TokenData

class AgentConfig(BaseModel):
    api_host: str
    api_port: int
    users: List[UserAgent]

def load_depictio_config():
    """
    Load the Depict.io configuration file.
    """
    try:
        with open(os.path.expanduser("~/.depictio/config.yaml"), "r") as f:
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

    return config


@app.command()
def show_config():
    depictio_agent_config = load_depictio_config()
    typer.echo(depictio_agent_config)


@app.command()
def test_login(email:str):
    depictio_agent_config = load_depictio_config()
    for user in depictio_agent_config.users:

        if user.email == email:
            typer.echo(f"User found: {user}")
            break
        
        # Connect to depictio API 
        url = f"http://{depictio_agent_config.host}:{depictio_agent_config.port}/api/v1/fetch_user/from_email"
        json = {"email": email}
        response = httpx.get(url, json=json)
        if response.status_code == 200:
            typer.echo(f"User found: {response.json()}")

        else: 
            typer.echo(f"User not found: {email}")
            raise typer.Exit(code=1)

    else:
        typer.echo(f"User not found: {email}")

@app.command()
def dummy():
    typer.echo("Dummy command.")

@app.command()
def test(param: str):
    typer.echo(f"Testing command with parameter: {param}")


def main():
    app()