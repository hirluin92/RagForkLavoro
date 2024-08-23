from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class CQASettings(BaseSettings):
    model_config = SettingsConfigDict()
    
    confidence_threshold: float = Field(alias='CQA_ConfidenceThreshold')
    default_noresult_answer: str = Field(alias='CQA_DefaultNoResultAnswer')
    deployment: str = Field(alias='CQA_Deployment')
    endpoint: str = Field(alias='CQA_Endpoint')
    key_credential: str = Field(alias='CQA_KeyCredential')
    knowledgebase_project: str = Field(alias='CQA_KnowledgeBaseProject')
    knowledgebase_project_dco: str = Field(alias='CQA_KnowledgeBaseProjectDCO')
    tags_dco: str = Field(alias='CQA_TagsDCO')