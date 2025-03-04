from pydantic import BaseModel


class ClassifyIntentResponse(BaseModel):
    intent: str = ""
    reason: str 
    numero_domus: list[int] = []
    stato_domanda: list[str] = []

