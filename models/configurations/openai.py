from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class OpenAISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='AZURE_OPENAI_')
    
    api_version: str
    completion_deployment_model: str
    completion_endpoint:str
    completion_key: str
    embedding_deployment_model: str
    embedding_endpoint: str
    embedding_key: str