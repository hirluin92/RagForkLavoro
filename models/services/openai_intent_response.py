from pydantic import BaseModel

class Dossier(BaseModel):
    numero_domus: list[int] = []
    stato_domanda: str =" "
    data: list[str] = []
    tipo_pratica: list[str] = []


class ClassifyIntentResponse(BaseModel):
    intent: str = ""
    reason: str 
    entities: Dossier
