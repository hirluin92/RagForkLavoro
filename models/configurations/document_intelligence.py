from pydantic_settings import BaseSettings, SettingsConfigDict

class DocumentIntelligenceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='DOCUMENT_INTELLIGENCE_')

    endpoint: str
    key: str