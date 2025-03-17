from typing import Optional
from pydantic import BaseModel

class DomusAnswerResponse(BaseModel):
    reason: Optional[str] = None
    answer: Optional[str] = None
    has_answer: Optional[bool] = False