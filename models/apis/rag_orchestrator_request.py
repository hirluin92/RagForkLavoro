from typing import Optional
from pydantic import BaseModel


class Interaction(BaseModel):
    question: str
    answer: str
    type: Optional[str] = "rag"


class PromptEditorCredential(BaseModel):
    type: str
    id: str
    version: Optional[str] = None
    
class RagConfiguration(BaseModel):
    id_monitor_form_app_integration: Optional[int] = False
    desc_monitor_form_app_integration: Optional[str] = None
    enable_cqa: Optional[bool] = True
    enable_enrichment: Optional[bool] = True
    


class RagOrchestratorRequest(BaseModel):
    query: str
    lang: Optional[str] = "it"
    llm_model_id: str
    tags: list[str] = []
    interactions: list[Interaction] = []
    environment: str = "production"
    prompts: list[PromptEditorCredential] = []
    token: Optional[str] = None
    user_fiscal_code: Optional[str] = None
    text_by_card: Optional[str] = None
    configuration: Optional[RagConfiguration] = None