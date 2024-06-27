from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class SearchSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='AZURE_SEARCH_')
    
    api_version: str
    endpoint:str
    index: str
    index_semantic_configuration: str
    k: int
    key: str