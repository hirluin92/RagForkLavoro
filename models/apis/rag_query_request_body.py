from pydantic import BaseModel


class RagQueryRequestBody(BaseModel):
    query: str
    llm_model_id: str
    tags: list[str] = []