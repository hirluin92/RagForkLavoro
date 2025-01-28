from pydantic import BaseModel


class DomusAnswerResponse(BaseModel):
    reason: str 
    answer: str
    has_answer: bool  