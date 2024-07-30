from abc import ABC, abstractmethod
from logging import Logger
import os

from aiohttp import ClientSession
from models.apis.enrichment_query_response import EnrichmentQueryResponse
from models.apis.rag_orchestrator_request import Interaction, RagOrchestratorRequest
from models.apis.rag_query_response_body import RagQueryResponse
from services.mssql import get_tags_by_tag_names

class AiQueryServiceBase(ABC):
     
    @staticmethod
    @abstractmethod
    def model_id(cls):
        raise NotImplementedError()
    
    @abstractmethod
    async def a_do_query(self, request: RagOrchestratorRequest,
                 logger: Logger,session: ClientSession) -> RagQueryResponse:
        pass
    
    @abstractmethod
    async def a_do_query_enrichment(self, request: RagOrchestratorRequest,
                            logger: Logger)-> EnrichmentQueryResponse:
        pass 

    def get_topic_from_tags(self, tags: list[str])->str:
        topic = ""
        tags_from_repo = get_tags_by_tag_names(tags)
        if len(tags_from_repo)>0:
            topic = ",".join([str(x.description) for x in tags_from_repo])
        return topic  

    def extract_chat_history(self, interactions: list[Interaction]) -> str:

        if not interactions or len(interactions) == 0:
            return ""

        formatted_strings = []

        for interaction in interactions:
            question = interaction.question
            answer = interaction.answer
            
            formatted_strings.append(f"user: {question}")
            formatted_strings.append(f"assistant: {answer}")
        
        newline = os.linesep
        result = newline.join(formatted_strings)

        return result 