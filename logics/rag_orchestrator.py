from logging import Logger

from aiohttp import ClientSession
from constants import event_types
from constants import llm as llm_const
from logics.ai_query_service_factory import AiQueryServiceFactory
from models.apis.rag_orchestrator_request import RagOrchestratorRequest
from models.apis.rag_orchestrator_response import RagOrchestratorResponse
from services.cqa import a_do_query as cqa_do_query

async def a_get_query_response(request: RagOrchestratorRequest,
            logger: Logger,
            session: ClientSession) -> RagOrchestratorResponse:
    # workaround per content filter:
    request.query = request.query.lower()
    cqa_result = await cqa_do_query(request.query, request.tags[0], logger)

    # Se CQA è in grado di gestire la richiesta restituisco subito la risposta
    if cqa_result:
        return RagOrchestratorResponse(cqa_result.text_answer,
                                       None,
                                       cqa_result.cqa_data,
                                       None)
    
    language_service = AiQueryServiceFactory.get_instance(request.llm_model_id)
    enriched_query = await language_service.a_do_query_enrichment(request, logger)

    if enriched_query.end_conversation:
        answer_to_return = llm_const.default_answer
        if len(enriched_query.end_conversation_reason)>0:
            answer_to_return = enriched_query.end_conversation_reason
        return RagOrchestratorResponse(answer_to_return,
                                   enriched_query.standalone_question,
                                   None,
                                   None)

    if enriched_query.standalone_question != request.query:
        request.query = enriched_query.standalone_question
        cqa_result = await cqa_do_query(request.query, request.tags[0], logger)
        # Se CQA è in grado di gestire la richiesta restituisco subito la risposta
        if cqa_result:
            logger.track_event(event_types.cqa_with_enrichment_event, 
                               { 
                                "originalQuestion": request.query, 
                                "normalizedQuestion": enriched_query.standalone_question
                                })   
            return RagOrchestratorResponse(cqa_result.text_answer,
                                       enriched_query.standalone_question,
                                       cqa_result.cqa_data,
                                       None)
    
    rag_query_result = await language_service.a_do_query(request, logger, session)
    # In caso non ci sia stata comunicazione con l'llm
    if len(rag_query_result.finish_reason) == 0:
        return RagOrchestratorResponse(rag_query_result.response,
                                   enriched_query.standalone_question,
                                   None,
                                   None)
    return RagOrchestratorResponse(rag_query_result.response,
                                   enriched_query.standalone_question,
                                   None,
                                   rag_query_result)