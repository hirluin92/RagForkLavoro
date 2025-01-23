from typing import Optional
from pydantic import BaseModel
    
class Interaction(BaseModel):
    question: str
    answer: str

class PromptEditorCredential(BaseModel):
    type: str
    id: str
    version: Optional[str] = None

class RagOrchestratorRequest(BaseModel):
    query: str  
    llm_model_id: str  
    tags: list[str] = []
    interactions: list[Interaction]  = []
    environment: str = "production"
    prompts: list[PromptEditorCredential] = []
    token: Optional[str] = None
    userFiscalCode: Optional[str] = None