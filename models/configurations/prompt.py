from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class PromptSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='PROMPT_')
    
    editor_api_key: str
    editor_endpoint: str
    enrichment_default_id: str
    enrichment_default_version: Optional[str] = None
    completion_default_id: str
    completion_default_version: Optional[str] = None
    msd_intent_recognition_default_id: str
    msd_intent_recognition_default_version: Optional[str] = None
    msd_completion_default_id: str
    msd_completion_default_version: Optional[str] = None