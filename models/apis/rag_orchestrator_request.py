from pydantic import BaseModel
    
class Interaction(BaseModel):
    question: str
    answer: str

class RagOrchestratorRequest(BaseModel):
    query: str  
    llm_model_id: str  
    tags: list[str] = []
    interactions: list[Interaction]  = []
    environment: str = "production"
