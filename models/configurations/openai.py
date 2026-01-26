from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class OpenAISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='AZURE_OPENAI_')
    
    # Endpoint sempre obbligatori (definiscono l'endpoint base Azure OpenAI)
    completion_endpoint: str
    embedding_endpoint: str
    
    # Campi opzionali: vengono recuperati da SQL tramite handle_access_control
    # Se presenti nelle env vars, vengono usati come fallback
    api_version: Optional[str] = None
    completion_deployment_model: Optional[str] = None
    completion_key: Optional[str] = None
    embedding_deployment_model: Optional[str] = None
    embedding_key: Optional[str] = None
    
    embedding_timeout: float = 30
    completion_key_storage_format: str = "{0}" #-Completion sarebbe da uniformare