from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class CQASettings(BaseSettings):
    model_config = SettingsConfigDict()
    
    endpoint: str = Field(alias='CQA_Endpoint')
    key_credential: str = Field(alias='CQA_KeyCredential')
    knowledgebase_project: str = Field(alias='CQA_KnowledgeBaseProject')
    deployment: str = Field(alias='CQA_Deployment')
    default_noresult_answer: str = Field(alias='CQA_DefaultNoResultAnswer')
    confidence_threshold: float = Field(alias='CQA_ConfidenceThreshold')
    auu_tags: str = Field(alias='CQA_AUU_TAGS')
    auu_project_name: str = Field(alias='CQA_AUU_PROJECT_NAME')