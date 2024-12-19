from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class MistralAISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='AZURE_MISTRALAI_')
    
    endpoint:str
    key: str
    model: str