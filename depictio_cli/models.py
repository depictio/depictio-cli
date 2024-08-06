
from datetime import datetime
import re
from typing import Dict, Optional, Tuple, List
from pydantic import BaseModel, field_validator
class TokenData(BaseModel):
    name: str
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
    is_admin: bool
    token: TokenData

class AgentConfig(BaseModel):
    api_base_url: str
    user: UserAgent

    @field_validator("api_base_url")
    def validate_api_base_url(cls, v):
        # check if the URL is valid using regex, starting with http:// or https:// and ending with port number
        if not re.match(r"http[s]?:\/\/.*:[0-9]+", v):  # noqa: F821
            raise ValueError("Invalid URL format")
        return v