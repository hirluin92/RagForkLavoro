from typing import Optional
from pydantic import BaseModel

class DomusAnswerResponse(BaseModel):
    reason: Optional[str] 
    answer: Optional[str]
    has_answer: Optional[bool]  