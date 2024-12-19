from pydantic_settings import BaseSettings, SettingsConfigDict

class PromptSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='PROMPT_')
    
    editor_api_key: str
    editor_endpoint: str
    enrichment_default_id: str
    enrichment_default_version: str
    completion_default_id: str
    completion_default_version: str