from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class AccessControlSettings(BaseSettings):
    model_config = SettingsConfigDict()

    enable_access_control: bool = True