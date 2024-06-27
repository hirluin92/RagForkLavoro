from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class OpenAISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='AZURE_OPENAI_')
    
    api_version: str
    completion_deployment_model: str
    completion_endpoint:str
    completion_key: str
    completion_temperature: float
    completion_tokens: int
    embedding_deployment_model: str
    embedding_endpoint: str
    embedding_key: str