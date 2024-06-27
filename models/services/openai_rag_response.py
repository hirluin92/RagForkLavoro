from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class RagResponse:
    response: str
    references: list[int]
    finish_reason: str

    @staticmethod
    def from_dict(content: any,
                  finish_reason = "") -> 'RagResponse':
        _response = str(content.get("response",
                                "Mi dispiace, non riesco a fornire una risposta alla tua domanda."))
        _references = [int(x) for x in content.get("references", [])]
        return RagResponse(_response, _references, finish_reason)
    
class RagResponseOutputParser(BaseModel):
    response: str
    references: list[int]
    finish_reason: str = "ND"