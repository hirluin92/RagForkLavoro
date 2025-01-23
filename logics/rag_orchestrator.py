from logging import Logger
from aiohttp import ClientSession
from constants import event_types
from constants import llm as llm_const
from logics.ai_query_service_factory import AiQueryServiceFactory
from models.apis.rag_orchestrator_request import RagOrchestratorRequest
from models.apis.rag_orchestrator_response import RagOrchestratorResponse
from models.apis.domus_form_applications_by_fiscal_code_request import DomusFormApplicationsByFiscalCodeRequest
#from models.apis.domus_form_applications_by_fiscal_code_response import DomusFormApplicationsByFiscalCodeResponse
#from models.apis.domus_form_application_details_request import DomusFormApplicationDetailsRequest
#from models.apis.domus_form_application_details_response import DomusFormApplicationDetailsResponse
from services.cqa import a_do_query as cqa_do_query
from services.prompt_editor import a_get_prompts_data
from services import openai
from services import mssql
from services import domus

async def a_get_query_response(request: RagOrchestratorRequest,
            logger: Logger,
            session: ClientSession) -> RagOrchestratorResponse:
    # workaround for content filter:
    request.query = request.query.lower()

    tag = request.tags[0]

    ######################## TEST ########################

    # test = await domus.a_get_form_applications_by_fiscal_code(
    #         DomusFormApplicationsByFiscalCodeRequest(request.userFiscalCode, request.token),
    #         session,
    #         logger)
    
    ################################################

    #CQA service response with original query
    cqa_result = await cqa_do_query(request.query, tag, logger)
    if cqa_result:
        return RagOrchestratorResponse(cqa_result.text_answer,
                                       None,
                                       cqa_result.cqa_data,
                                       None)
    
    prompt_type_filter = [llm_const.completion, llm_const.enrichment, llm_const.msd_completion, llm_const.msd_intent_recognition]

    list_prompt_version_info = await mssql.a_get_prompt_info(logger, tag, prompt_type_filter)

    #API get prompts
    (enrichment_prompt_data, 
    completion_prompt_data, 
    msd_intent_recognition_prompt_data,
    msd_completion_prompt_data) = await a_get_prompts_data(request.prompts, list_prompt_version_info, logger, session)

    if enrichment_prompt_data == None:
        raise Exception("No enrichment_prompt_data found.")

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
        cqa_result = await cqa_do_query(request.query, tag, logger)
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
    
    if msd_intent_recognition_prompt_data == None:
        raise Exception("No enrichment_prompt_data found.")
    
    #  verifica riconoscimento entità
    test = await openai.a_get_msd_intent_recognition(request.query, logger=logger)

    # se sì, riconoscimento utente autenticato
    if test:
        a = 0
        list_forms = await domus.a_get_form_applications_by_fiscal_code(
            DomusFormApplicationsByFiscalCodeRequest(request.userFiscalCode, request.userFiscalCode),
            session,
            logger)
        # se sì, chiamare servizio domus
        # verificare risposta prompt completion finale con domus
        if test: # se sì, mostrare all'utente
            a = 0
        else: # se no, RAG
            a = 0
    else: # se no, RAG
        a = 0
    
    # if msd_completion_prompt_data == None:
    #     raise Exception("No enrichment_prompt_data found.")

    if completion_prompt_data == None:
        raise Exception("No enrichment_prompt_data found.")

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