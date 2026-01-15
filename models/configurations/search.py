from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class SearchSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='AZURE_SEARCH_')

    api_version: str
    endpoint: str
    index: str
    index_production: str
    index_semantic_configuration: str
    k: int
    key: str
    search_method: str = "HYBRID"
    semantic_ranking_enabled: bool = True
    top: int
    authentication_method: str = "APIKey"

    @classmethod
    @field_validator("search_method")
    def validate_search_method(cls, v):
        if v not in ["HYBRID", "VECTOR", "FULL-TEXT"]:
            raise ValueError("Invalid search_method value")
        return v

    @classmethod
    @field_validator("authentication_method")
    def validate_search_method(cls, v):
        if v not in ["APIKey", "RBAC"]:
            raise ValueError("Invalid authentication_method value")
        return v