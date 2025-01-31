import json
from logging import Logger
from aiohttp import ClientSession
from constants import event_types
from constants import llm as llm_const
from logics.ai_query_service_factory import AiQueryServiceFactory
from models.apis.domus_form_application_details_request import DomusFormApplicationDetailsRequest
from models.apis.enrichment_query_response import EnrichmentQueryResponse
from models.apis.prompt_editor_response_body import PromptEditorResponseBody
from models.apis.rag_orchestrator_request import RagOrchestratorRequest
from models.apis.rag_orchestrator_response import RagOrchestratorResponse
from models.apis.rag_orchestrator_response import MonitorFormApplication
from models.apis.rag_orchestrator_response import EventMonitorFormApplication
from models.apis.domus_form_applications_by_fiscal_code_request import DomusFormApplicationsByFiscalCodeRequest
#from models.apis.domus_form_applications_by_fiscal_code_response import DomusFormApplicationsByFiscalCodeResponse
#from models.apis.domus_form_application_details_request import DomusFormApplicationDetailsRequest
#from models.apis.domus_form_application_details_response import DomusFormApplicationDetailsResponse
from models.configurations.prompt import PromptSettings
from services.cqa import a_do_query as cqa_do_query
from services import prompt_editor
from services import openai
from services import mssql
from services import domus
from utils import string

async def a_get_query_response(request: RagOrchestratorRequest,
            logger: Logger,
            session: ClientSession) -> RagOrchestratorResponse:
    # workaround for content filter:
    
    request.query = f"{request.query}. {request.text_by_card}." if request.text_by_card != None and len(request.text_by_card) > 0 else request.query
    request.query = request.query.lower()

    tag = request.tags[0]

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
    msd_completion_prompt_data) = await prompt_editor.a_get_prompts_data(request.prompts, list_prompt_version_info, logger, session)

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
    
    result = await check_msd_question(request, 
                    tag,
                    msd_completion_prompt_data, 
                    msd_intent_recognition_prompt_data, 
                    language_service,
                    enriched_query,
                    completion_prompt_data,
                    logger,
                    session)
    
    return result if result is not None else await a_do_query(request, completion_prompt_data, language_service, enriched_query, logger, session) 
    
async def a_do_query(request: RagOrchestratorRequest, 
                     completion_prompt_data: PromptEditorResponseBody, 
                     language_service: AiQueryServiceFactory,
                     enriched_query: EnrichmentQueryResponse,
                     logger: Logger,
                     session: ClientSession) -> RagOrchestratorResponse:
    
    if completion_prompt_data == None:
        raise Exception("No enrichment_prompt_data found.")
    
    #Compute completion
    rag_query_result = await language_service.a_do_query(request, completion_prompt_data, logger, session)
    
    return RagOrchestratorResponse(rag_query_result.response,
                                enriched_query.standalone_question,
                                None,
                                None if len(rag_query_result.finish_reason) == 0 else rag_query_result)
    
    
async def check_msd_question(request: RagOrchestratorRequest, 
                    tag: string,
                    msd_completion_prompt_data: PromptEditorResponseBody, 
                    msd_intent_recognition_prompt_data: PromptEditorResponseBody, 
                    language_service: AiQueryServiceFactory,
                    enriched_query: EnrichmentQueryResponse,
                    completion_prompt_data: PromptEditorResponseBody,
                    logger: Logger,
                    session: ClientSession) -> RagOrchestratorResponse:

    if msd_intent_recognition_prompt_data == None:
        raise Exception("No msd_intent_recognition_prompt_data found.")
        
    # If the tag application is disabled for "monitoring the application status" integration, the rag will directly response
    if await mssql.a_check_status_tag_for_mst(logger, tag, False):
        return None
        
    #  Intent recognition
    intent_prompt_data = PromptEditorResponseBody(msd_intent_recognition_prompt_data.version, msd_intent_recognition_prompt_data.llm_model,
                                                msd_intent_recognition_prompt_data.prompt, msd_intent_recognition_prompt_data.parameters, 
                                                msd_intent_recognition_prompt_data.model_parameters)
    
    intent_result = await language_service.a_compute_classify_intent_query(request, intent_prompt_data, logger)
    
    # If the correct intent has not been recognized from the user's sentence, the rag will directly response
    if intent_result.intent.lower() == 'altro':
        return None
        
    # riconoscimento utente autenticato
    if string.is_null_or_empty_or_whitespace(request.user_fiscal_code) or string.is_null_or_empty_or_whitespace(request.token):
        # User not authenticated
        return RagOrchestratorResponse("", "", None, "", 
                                    MonitorFormApplication(event_type=EventMonitorFormApplication.user_not_authenticated))
    
    settings = PromptSettings()
    (domus_form_application_code, domus_form_application_name) = await prompt_editor.a_get_form_application_name_by_tag(settings.config_container, tag, logger)
    
    list_forms = await domus.a_get_form_applications_by_fiscal_code(
        DomusFormApplicationsByFiscalCodeRequest(request.user_fiscal_code, request.token, domus_form_application_code, intent_result.stato_domanda[0] if intent_result.stato_domanda else None),
        session,
        logger)
        
    if list_forms is None or list_forms.listaDomande is None or len(list_forms.listaDomande) == 0:
        # There are no form application submitted by the client with the specified tag, the rag will directly response
        return None

    # TEST
    # one_form = list_forms.listaDomande[0]
    
    # list_forms.listaDomande = []
    # list_forms.listaDomande.append(one_form)
    
    if len(list_forms.listaDomande) > 1:
        # return carousel
        return RagOrchestratorResponse("", "", None, "", 
                                    MonitorFormApplication(answer_list=[request.model_dump() for request in list_forms.listaDomande],
                                        event_type=EventMonitorFormApplication.show_answer_list))
    
    user_form_application = list_forms.listaDomande[0]
    domus_number = user_form_application.numeroDomus
    progressivo_istanza = user_form_application.progressivoIstanza
    
    form_application_details = await domus.a_get_form_application_details(DomusFormApplicationDetailsRequest(domus_number, progressivo_istanza, request.token), 
                                                                          session, logger)
    
    if msd_completion_prompt_data == None:
        raise Exception("No enrichment_prompt_data found.")

    domus_prompt_data = PromptEditorResponseBody(msd_completion_prompt_data.version, msd_completion_prompt_data.llm_model,
                                    msd_completion_prompt_data.prompt, msd_completion_prompt_data.parameters, 
                                    msd_completion_prompt_data.model_parameters)
    
    domus_result = await language_service.a_get_domus_answer(request, form_application_details, domus_prompt_data, logger)

    if domus_result:
        if domus_result.has_answer and domus_result.answer:
            return RagOrchestratorResponse("", "", None, "", 
                                    MonitorFormApplication(answer_text=domus_result.answer,
                                        event_type=EventMonitorFormApplication.show_answer_text))
            
        return await a_do_query(request, completion_prompt_data, language_service, enriched_query, logger, session) 
    
    return None