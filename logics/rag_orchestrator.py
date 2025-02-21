import json
from aiohttp import ClientResponseError, ClientSession
from constants import clog, event_types
from constants import llm as llm_const
from logics.ai_query_service_factory import AiQueryServiceFactory
from models.apis.domus_form_application_details_request import DomusFormApplicationDetailsRequest
from models.apis.domus_form_applications_by_fiscal_code_response import DomusFormApplicationsByFiscalCodeResponse
from models.apis.enrichment_query_response import EnrichmentQueryResponse
from models.apis.prompt_editor_response_body import PromptEditorResponseBody
from models.apis.rag_orchestrator_request import RagOrchestratorRequest
from models.apis.rag_orchestrator_response import RagOrchestratorResponse
from models.apis.rag_orchestrator_response import MonitorFormApplication
from models.apis.rag_orchestrator_response import EventMonitorFormApplication
from models.apis.domus_form_applications_by_fiscal_code_request import DomusFormApplicationsByFiscalCodeRequest
from models.configurations.clog import CLog, CLogParams, CLogSettings
from models.configurations.prompt import PromptSettings
from services.cqa import a_do_query as cqa_do_query
from services.logging import Logger
from services.prompt_editor import a_get_prompts_data, a_get_form_application_name_by_tag
from services import openai
from services.mssql import a_get_prompt_info, a_check_status_tag_for_mst
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

    list_prompt_version_info = await a_get_prompt_info(logger, tag, prompt_type_filter)

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
    
    if request.disable_mst_integration:
        return await a_do_query(request, completion_prompt_data, language_service, enriched_query, logger, session) 
    
    result = await check_msd_question(request, 
                    tag,
                    msd_completion_prompt_data, 
                    msd_intent_recognition_prompt_data, 
                    language_service,
                    enriched_query,
                    completion_prompt_data,
                    logger,
                    session)
    
    if result is None or (result.monitor_form_application is None and result.clog is not None):
        return await a_do_query(request, completion_prompt_data, language_service, enriched_query, logger, session, clog=getattr(result, 'clog', None)) 
    
    return result
    
async def a_do_query(request: RagOrchestratorRequest, 
                     completion_prompt_data: PromptEditorResponseBody, 
                     language_service: AiQueryServiceFactory,
                     enriched_query: EnrichmentQueryResponse,
                     logger: Logger,
                     session: ClientSession,
                     clog : CLog = None,
                     domusData: str = None) -> RagOrchestratorResponse:
    
    if completion_prompt_data == None:
        raise Exception("No enrichment_prompt_data found.")
    
    #Compute completion
    rag_query_result = await language_service.a_do_query(request, completion_prompt_data, logger, session, domusData)
    
    return RagOrchestratorResponse(rag_query_result.response,
                                enriched_query.standalone_question,
                                None,
                                None if len(rag_query_result.finish_reason) == 0 else rag_query_result,
                                clog = clog or None)
    
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
    if await a_check_status_tag_for_mst(logger, tag, False):
        return None
        
    # Intent recognition
    intent_prompt_data = msd_intent_recognition_prompt_data
    
    intent_result = await language_service.a_compute_classify_intent_query(request, intent_prompt_data, logger)
    
    # If the correct intent has not been recognized from the user's sentence, the rag will directly response
    if intent_result.intent.lower() == 'altro':
        return None
        
    # riconoscimento utente autenticato
    if string.is_null_or_empty_or_whitespace(request.user_fiscal_code) or string.is_null_or_empty_or_whitespace(request.token):
        # User not authenticated
        return RagOrchestratorResponse("", "", None, "", 
                                    MonitorFormApplication(event_type=EventMonitorFormApplication.user_not_authenticated))
    
    prompt_settings = PromptSettings()
    (domus_form_application_code, domus_form_application_name) = await a_get_form_application_name_by_tag(prompt_settings.config_container, tag, logger)
    
    clog_settings = CLogSettings()
    
    try:
        list_forms = await domus.a_get_form_applications_by_fiscal_code(
            DomusFormApplicationsByFiscalCodeRequest(request.user_fiscal_code, request.token, domus_form_application_code, 
                                                     intent_result.stato_domanda[0] if intent_result.stato_domanda and len(intent_result.stato_domanda) > 0 else None),
            session,
            logger)
        
    except ClientResponseError as e:
        logger.exception(e)
        return RagOrchestratorResponse("", "", None, "", None, 
                                       CLog(ret_code=e.code, err_desc=clog.DOMUSAPIERROR, id_event=clog_settings.msd_elencodomande, 
                                            params=CLogParams(cf=request.user_fiscal_code, prestazione=tag)))
    
    except Exception as e:
        logger.exception(e)
        return RagOrchestratorResponse("", "", None, "", None, 
                                       CLog(ret_code=500, err_desc=clog.DOMUSAPIERROR, id_event=clog_settings.msd_elencodomande, 
                                            params=CLogParams(cf=request.user_fiscal_code, prestazione=tag)))
        
    if list_forms and (list_forms.errore or not string.is_null_or_empty_or_whitespace(list_forms.messaggioErrore)):
        return RagOrchestratorResponse("", "", None, "", None, 
                                       CLog(ret_code=200, err_desc=clog.DOMUSAPIOKERRORPARAMISTRUE, id_event=clog_settings.msd_elencodomande, 
                                            params=CLogParams(cf=request.user_fiscal_code, prestazione=tag)))
        
    if list_forms is None or not list_forms.listaDomande:
        return RagOrchestratorResponse("", "", None, "", None, 
                                       CLog(ret_code=200, err_desc=clog.DOMUSAPIOKLISTEMPTY, id_event=clog_settings.msd_elencodomande, 
                                            params=CLogParams(cf=request.user_fiscal_code, prestazione=tag)))
        
        
    if len(list_forms.listaDomande) > 1:
        if string.is_null_or_empty_or_whitespace(request.text_by_card) or len(intent_result.numero_domus) == 0:
            return RagOrchestratorResponse("", "", None, "", 
                                        MonitorFormApplication(answer_list=[request.model_dump() for request in list_forms.listaDomande],
                                            event_type=EventMonitorFormApplication.show_answer_list),
                                        CLog(ret_code=0, id_event=clog_settings.msd_elencodomande, 
                                             params=CLogParams(cf=request.user_fiscal_code, prestazione=tag)))
        else: 
            user_form_application = next((domanda for domanda in list_forms.listaDomande if domanda.numeroDomus == str(intent_result.numero_domus[0])), None)
    else:   
        user_form_application = list_forms.listaDomande[0]
        
    if not user_form_application:
        # There are no form application submitted by the client with the specified "numero domus", so the rag will directly response
        return None
        
    try:
        form_application_details = await domus.a_get_form_application_details(
        DomusFormApplicationDetailsRequest(user_form_application.numeroDomus, user_form_application.progressivoIstanza, request.token), 
        session, logger)
    
    except ClientResponseError as e:
        logger.exception(e)
        return RagOrchestratorResponse("", "", None, "", None, 
                                       CLog(ret_code=e.code, err_desc=clog.DOMUSAPIDETAILERROR, id_event=clog_settings.msd_dettagliodomande, 
                                            params=CLogParams(cf=request.user_fiscal_code, prestazione=tag, 
                                                                num_domus=user_form_application.numeroDomus, 
                                                                num_prot=user_form_application.numeroProtocollo)))

    except Exception as e:
        logger.exception(e)
        return RagOrchestratorResponse("", "", None, "", None, 
                                        clog=CLog(ret_code=500, err_desc=clog.DOMUSAPIDETAILERROR, id_event=clog_settings.msd_dettagliodomande, 
                                                params=CLogParams(cf=request.user_fiscal_code, prestazione=tag, 
                                                                  num_domus=user_form_application.numeroDomus, 
                                                                  num_prot=user_form_application.numeroProtocollo)))
        
    if form_application_details and (form_application_details.errore or not string.is_null_or_empty_or_whitespace(form_application_details.messaggioErrore)):
        return RagOrchestratorResponse("", "", None, "", None, 
                                       clog=CLog(ret_code=200, err_desc=clog.DOMUSAPIDETAILERRORPARAMISTRUE, id_event=clog_settings.msd_dettagliodomande, 
                                            params=CLogParams(cf=request.user_fiscal_code, prestazione=tag, 
                                                                  num_domus=user_form_application.numeroDomus, 
                                                                  num_prot=user_form_application.numeroProtocollo)))
        
    if form_application_details is None:
        return RagOrchestratorResponse("", "", None, "", None, 
                                       CLog(ret_code=200, err_desc=clog.DOMUSAPIOKDETAILEMPTY, id_event=clog_settings.msd_dettagliodomande, 
                                            params=CLogParams(cf=request.user_fiscal_code, prestazione=tag, 
                                                                  num_domus=user_form_application.numeroDomus, 
                                                                  num_prot=user_form_application.numeroProtocollo)))
        
    if msd_completion_prompt_data == None:
        raise Exception("No enrichment_prompt_data found.")

    domus_prompt_data = msd_completion_prompt_data
        
    domus_result = await language_service.a_get_domus_answer(request, form_application_details, domus_prompt_data, logger)

    if domus_result:
        if domus_result.has_answer and domus_result.answer:
            return RagOrchestratorResponse("", "", None, "", 
                                    MonitorFormApplication(answer_text=domus_result.answer,event_type=EventMonitorFormApplication.show_answer_text),
                                    CLog(ret_code=0, id_event=clog_settings.msd_dettagliodomande,
                                         params=CLogParams(cf=request.user_fiscal_code, prestazione=tag, 
                                                           num_domus=user_form_application.numeroDomus,
                                                           num_prot=user_form_application.numeroProtocollo)))
        
    return await a_do_query(request, completion_prompt_data, language_service, enriched_query, logger, session, 
                            domusData=str(form_application_details.model_dump()),
                            clog=CLog(ret_code=0, params=CLogParams(cf=request.user_fiscal_code, prestazione=tag, 
                                                                  num_domus=user_form_application.numeroDomus, 
                                                                  num_prot=user_form_application.numeroProtocollo)))