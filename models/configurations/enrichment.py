from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class EnrichmentSettings(BaseSettings):
    model_config = SettingsConfigDict()

    system_template_path: str = Field(alias= "Enrichment_SystemTemplatePath")
    user_template_path: str = Field(alias= "Enrichment_UserTemplatePath")
    tags_file_path: str = Field(alias= "Enrichment_TagsFilePath")
