from logging import Logger

from aiohttp import ClientSession
from logics.ai_query_service_base import AiQueryServiceBase
from logics.rag_query import a_execute_query
from models.apis.prompt_editor_response_body import PromptEditorResponseBody
from models.apis.rag_orchestrator_request import RagOrchestratorRequest
from models.apis.enrichment_query_response import EnrichmentQueryResponse
from models.apis.rag_query_response_body import RagQueryResponse
import constants.llm as llm_const
from models.services.openai_domus_response import DomusAnswerResponse
from models.services.openai_intent_response import ClassifyIntentResponse
from services.openai import a_get_answer_from_domus, a_get_enriched_query, a_get_intent_from_enriched_query

class AiQueryServiceOpenAI(AiQueryServiceBase):

    @staticmethod
    def model_id():
            return llm_const.openai
    
    async def a_do_query_enrichment(self, request: RagOrchestratorRequest,
                                    prompt_data: PromptEditorResponseBody,
                                logger: Logger) -> EnrichmentQueryResponse:
        # Creazione chat history
        chat_history = self.extract_chat_history(request.interactions)
        topic = await self.get_topic_from_tags(logger, request.tags)
        query_enrichment_result = await a_get_enriched_query(request.query,
                                                     topic,
                                                     chat_history,
                                                     prompt_data,
                                                     logger)
        return query_enrichment_result

    async def a_do_query(self, request: RagOrchestratorRequest,
                         prompt_data: PromptEditorResponseBody,
                        logger: Logger,
                        session: ClientSession)-> RagQueryResponse:
        query_result = await a_execute_query(request, 
                                             prompt_data,
                                             logger, 
                                             session)
        return query_result
    
    async def a_compute_classify_intent_query(self, request: RagOrchestratorRequest, prompt_data: PromptEditorResponseBody,
                            logger: Logger) -> ClassifyIntentResponse: 
         result = await a_get_intent_from_enriched_query(request.query, prompt_data, logger)
         return result
    
    async def a_get_domus_answer(self, request: RagOrchestratorRequest, practice_detail: str, prompt_data: PromptEditorResponseBody,
                            logger: Logger) -> DomusAnswerResponse:
         result = await a_get_answer_from_domus(request.query, practice_detail, prompt_data, logger)
         return result