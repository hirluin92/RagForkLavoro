from logging import Logger

from aiohttp import ClientSession
from pydantic import ValidationError
import requests
from constants import event_types
from constants import llm as llm_const
from logics.ai_query_service_factory import AiQueryServiceFactory
from models.apis.rag_orchestrator_request import RagOrchestratorRequest
from models.apis.rag_orchestrator_response import RagOrchestratorResponse
from services.cqa import a_do_query as cqa_do_query
from services.prompt_editor import a_get_completion_prompt_data, a_get_enrichment_prompt_data  
from utils.http_problem import Problem

async def a_get_query_response(request: RagOrchestratorRequest,
            logger: Logger,
            session: ClientSession) -> RagOrchestratorResponse:
    # workaround for content filter:
    request.query = request.query.lower()

    #CQA service response with original query
    cqa_result = await cqa_do_query(request.query, request.tags[0], logger)
    if cqa_result:
        return RagOrchestratorResponse(cqa_result.text_answer,
                                       None,
                                       cqa_result.cqa_data,
                                       None)
    #API get prompts
    enrichment_prompt_data = await a_get_enrichment_prompt_data(request.prompts, logger, session)
    completion_prompt_data = await a_get_completion_prompt_data(request.prompts, logger, session)

    #Verify llm model id request and prompts model from editor
    if(request.llm_model_id != enrichment_prompt_data.llm_model or 
       request.llm_model_id != completion_prompt_data.llm_model):
            raise Exception("The request llm model id  is different from prompt editor llm model.")
    
    #Get AI service (OpenAI or Mistral)
    language_service = AiQueryServiceFactory.get_instance(request.llm_model_id)

    #Compute enrichment
    enriched_query = await language_service.a_do_query_enrichment(request, enrichment_prompt_data, logger)
    if enriched_query.end_conversation:
        answer_to_return = llm_const.default_answer
        if len(enriched_query.end_conversation_reason)>0:
            answer_to_return = enriched_query.end_conversation_reason
        return RagOrchestratorResponse(answer_to_return,
                                   enriched_query.standalone_question,
                                   None,
                                   None)

    #CQA service response with query enriched
    if enriched_query.standalone_question != request.query:
        request.query = enriched_query.standalone_question
        cqa_result = await cqa_do_query(request.query, request.tags[0], logger)
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
    
    #Compute completion
    rag_query_result = await language_service.a_do_query(request, completion_prompt_data, logger, session)
    #case: no AI response
    if len(rag_query_result.finish_reason) == 0:
        return RagOrchestratorResponse(rag_query_result.response,
                                   enriched_query.standalone_question,
                                   None,
                                   None)
    return RagOrchestratorResponse(rag_query_result.response,
                                   enriched_query.standalone_question,
                                   None,
                                   rag_query_result)