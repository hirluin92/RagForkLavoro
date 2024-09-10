from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict()

    enrichment_by_topic_enabled: bool = Field(alias= "ENRICHMENT_BY_TOPIC_ENABLED")
