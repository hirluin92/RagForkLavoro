from logging import Logger

from aiohttp import ClientSession
from logics.ai_query_service_base import AiQueryServiceBase
from logics.rag_query import a_execute_query
from models.apis.enrichment_query_response import EnrichmentQueryResponse
from models.apis.rag_orchestrator_request import RagOrchestratorRequest
import constants.llm as llm_const
from models.apis.rag_query_response_body import RagQueryResponse

from services.mistralai import a_get_enriched_query

class AiQueryServiceMistralAI(AiQueryServiceBase):

    @staticmethod
    def model_id():
            return llm_const.mistralai
    
    async def a_do_query_enrichment(self, request: RagOrchestratorRequest,
                            logger: Logger) -> EnrichmentQueryResponse:
        # Creazione chat history
        chat_history = self.extract_chat_history(request.interactions)
        topic = await self.get_topic_from_tags(request.tags)
        query_enrichment_result = await a_get_enriched_query(request.query,
                                                     topic,
                                                     chat_history,
                                                     logger)
        return query_enrichment_result

    async def a_do_query(self, request: RagOrchestratorRequest,
                 logger: Logger,session: ClientSession)-> RagQueryResponse:
        query_result = await a_execute_query(request,
                                             logger,
                                             session)
        return query_result