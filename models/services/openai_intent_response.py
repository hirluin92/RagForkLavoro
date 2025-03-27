from pydantic import BaseModel


class ClassifyIntentResponse(BaseModel):
    intent: str = ""
    reason: str 
    numero_domus: list[str] = []
    numero_protocollo: list[str] = []
    stato_domanda: list[str] = []

