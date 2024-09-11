from pydantic import BaseModel


class EnrichmentQueryResponse(BaseModel):
    standalone_question: str = ""
    end_conversation: bool = False
    end_conversation_reason: str = ""
