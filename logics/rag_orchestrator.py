from dataclasses import asdict
import json
from aiohttp import ClientResponseError, ClientSession
from constants import clog, event_types, monitor_form_app
from constants import llm as llm_const
from logics.ai_query_service_factory import AiQueryServiceFactory
from models.apis.domus_form_application_details_request import DomusFormApplicationDetailsRequest
from models.apis.domus_form_application_details_response import DomusFormApplicationDetailsResponse
from models.apis.domus_form_applications_by_fiscal_code_response import DomusFormApplicationsByFiscalCodeResponse
from models.apis.enrichment_query_response import EnrichmentQueryResponse
from models.apis.prompt_editor_response_body import PromptEditorResponseBody
from models.apis.rag_orchestrator_request import Interaction, RagOrchestratorRequest
from models.apis.rag_orchestrator_response import RagOrchestratorResponse
from models.apis.rag_orchestrator_response import MonitorFormApplication
from models.apis.rag_orchestrator_response import EventMonitorFormApplication
from models.apis.domus_form_applications_by_fiscal_code_request import DomusFormApplicationsByFiscalCodeRequest
from models.configurations.clog import CLog, CLogParams, CLogSettings
from models.configurations.msd import MsdSettings
from models.configurations.prompt import PromptSettings
from models.configurations.storage import BlobStorageSettings
from models.services.mssql_tag import EnumMonitorFormApplication, MsSqlTag
from services.cqa import a_do_query as cqa_do_query
from services.logging import Logger
from services.prompt_editor import a_get_prompts_data, a_get_form_application_name_by_tag
from services import openai
from services.mssql import a_get_prompt_info, a_check_status_tag_for_mst, a_get_tags_by_tag_names
from services import domus
from services import storage
from utils import string
from services import redis as redisService

async def a_get_query_response(request: RagOrchestratorRequest,
            logger: Logger,
            session: ClientSession) -> RagOrchestratorResponse:
    
    #request.query = f"{request.query}. {request.text_by_card}." if request.text_by_card != None and len(request.text_by_card) > 0 else request.query
    request.query = request.text_by_card if request.text_by_card != None and len(request.text_by_card) > 0 else request.query
    
    # workaround for content filter:
    request.query = request.query.lower()

    tag = request.tags[0]
    
    tags_info = await a_get_tags_by_tag_names(logger, request.tags)
    
    if not tags_info or len(tags_info) == 0:
        raise Exception(f"No tags {request.tags} found.")

    tag_info = tags_info[0]
    
    logger.track_event(event_types.rag_orchestrator_tag_info_by_db,
                               {
                                   "tag_info":  json.dumps(asdict(tag_info), ensure_ascii=False).encode('utf-8')
                               })
    
    tag_info.id_monitoring_question = request.configuration.id_monitor_form_app_integration if request.configuration and request.configuration.id_monitor_form_app_integration else tag_info.id_monitoring_question
    tag_info.desc_monitoring_question = EnumMonitorFormApplication.get_enum_name(tag_info.id_monitoring_question)

    tag_info.enable_cqa = True if request.configuration and request.configuration.enable_cqa or ((request.configuration == None or request.configuration.enable_cqa == None) and tag_info.enable_cqa) else False
    tag_info.enable_enrichment = True if request.configuration and request.configuration.enable_enrichment or ((request.configuration == None or request.configuration.enable_enrichment == None) and tag_info.enable_enrichment) else False

    logger.track_event(event_types.rag_orchestrator_tag_info_by_request,
                            {
                                "tag_info":  json.dumps(asdict(tag_info), ensure_ascii=False).encode('utf-8')
                            })

    if tag_info.enable_cqa:
        #CQA service response with original query
        cqa_result = await cqa_do_query(request.query, tag, logger)
        if cqa_result:
            return RagOrchestratorResponse(cqa_result.text_answer,
                                        None,
                                        cqa_result.cqa_data,
                                        None)
    
    prompt_type_filter = [llm_const.completion, llm_const.enrichment, llm_const.msd_completion, llm_const.msd_intent_recognition]

    list_prompt_version_info = await a_get_prompt_info(logger, tag, prompt_type_filter, request.llm_model_id)

    # API get prompts
    (enrichment_prompt_data,
     completion_prompt_data,
     msd_intent_recognition_prompt_data,
     msd_completion_prompt_data) = await a_get_prompts_data(request.prompts, list_prompt_version_info, logger, session)

    if enrichment_prompt_data == None:
        raise Exception("No enrichment_prompt_data found.")

    # Verify llm model id request and prompts model from editor
    if (request.llm_model_id != enrichment_prompt_data.llm_model or
            request.llm_model_id != completion_prompt_data.llm_model):
        raise Exception(
            "The request LLM model ID is different from Prompt Editor LLM model.")

    # Get AI service (OpenAI or Mistral)
    language_service = AiQueryServiceFactory.get_instance(request.llm_model_id)

    enriched_query = EnrichmentQueryResponse(standalone_question=request.query)
    
    if tag_info.enable_enrichment:
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
            
        request.query = enriched_query.standalone_question

    if tag_info.enable_cqa and tag_info.enable_enrichment:
        #CQA service response with query enriched
        if enriched_query.standalone_question != request.query:
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
    
    #monitor_form_app_history = next((interaction for interaction in request.interactions if interaction.type.lower() == monitor_form_app.type), None)
    
    if tag_info.id_monitoring_question == EnumMonitorFormApplication.OnlyRag.value:
        return await a_do_query(request, completion_prompt_data, language_service, enriched_query, logger, session) 
    
    result = await check_msd_question(request, 
                    tag,
                    msd_completion_prompt_data, 
                    msd_intent_recognition_prompt_data, 
                    language_service,
                    enriched_query,
                    completion_prompt_data,
                    tag_info,
                    logger,
                    session)
    
    if tag_info.id_monitoring_question == EnumMonitorFormApplication.Rag_MonitoringQuestion.value and (result is None or (result.monitor_form_application is None and result.clog is not None)):
        return await a_do_query(request, completion_prompt_data, language_service, enriched_query, logger, session, clog=getattr(result, 'clog', None)) 
    
    return result


async def a_do_query(request: RagOrchestratorRequest,
                     completion_prompt_data: PromptEditorResponseBody,
                     language_service: AiQueryServiceFactory,
                     enriched_query: EnrichmentQueryResponse,
                     logger: Logger,
                     session: ClientSession,
                     clog: CLog = None,
                     domusData: str = None) -> RagOrchestratorResponse:

    if completion_prompt_data == None:
        raise Exception("No enrichment_prompt_data found.")

    # Compute completion
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
                    tag_info: MsSqlTag,
                    logger: Logger,
                    session: ClientSession) -> RagOrchestratorResponse:

    redis = False
    wrong_input = False
    redisCache = None
    carosello= False
    dettaglioDomus= False
    dettaglioProto = False
 
    
    msd_settings = MsdSettings()
    clog_settings = CLogSettings()
    
    clog_params = CLogParams(cf=request.user_fiscal_code, prestazione=tag)
    clog_last_status = CLog(ret_code=0, err_desc=None, id_event=clog_settings.msd_elencodomande, params=clog_params)
    
    # Intent recognition
    intent_prompt_data = msd_intent_recognition_prompt_data
        
    intent_result = await language_service.a_compute_classify_intent_query(request, intent_prompt_data, logger)

     # If the correct intent has not been recognized from the user's sentence, the rag will directly response
    if intent_result.intent.lower() == 'altro':
        return None
    

    
    # recupera cache redis
    # redis service
    if not request.conversation_id:
      logger.exception('request.conversation_id is null')
    else:
        if not intent_result.numero_domus and not intent_result.numero_protocollo:
            carosello = True
            key=redisService.make_key("list",request.conversation_id)
            redisCache = redisService.get_from_redis(key)
        elif intent_result.numero_domus:
            dettaglioDomus = True
            key=redisService.make_key("dett",request.conversation_id,intent_result.numero_domus[0])
            redisCache = redisService.get_from_redis(key)
        elif intent_result.numero_protocollo:
            dettaglioProto= True
            key=redisService.make_key("dett",request.conversation_id,intent_result.numero_protocollo[0])
            redisCache = redisService.get_from_redis(key)

    if not redisCache:
        if msd_intent_recognition_prompt_data == None:
            raise Exception("No msd_intent_recognition_prompt_data found.")
            
            
        # riconoscimento utente autenticato
        if string.is_null_or_empty_or_whitespace(request.user_fiscal_code) or string.is_null_or_empty_or_whitespace(request.token):
            # User not authenticated
            return RagOrchestratorResponse("", "", None, "", 
                                        MonitorFormApplication(event_type=EventMonitorFormApplication.user_not_authenticated))
        
        prompt_settings = PromptSettings()
        (domus_form_application_code, domus_form_application_name) = await a_get_form_application_name_by_tag(prompt_settings.config_container, tag, logger)
        user_form_application = None
        
        try:
            try:
                list_forms = await domus.a_get_form_applications_by_fiscal_code(
                    DomusFormApplicationsByFiscalCodeRequest(request.user_fiscal_code, request.token, domus_form_application_code, 
                                                            intent_result.stato_domanda[0] if intent_result.stato_domanda and len(intent_result.stato_domanda) > 0 else None),
                    session,
                    logger)
             
                logger.track_event(event_types.event_track_log_intent_result, {"Intent_result" : json.dumps(intent_result, default=custom_serializer)})
                logger.track_event(event_types.event_track_log_intent_result, {"list_forms" : json.dumps(list_forms, default=custom_serializer)})
                
            except ClientResponseError as e:
                logger.exception(e)
                clog_last_status.ret_code=e.code
                clog_last_status.err_desc=clog.DOMUSAPIERROR
                return RagOrchestratorResponse("", "", None, "", None, clog_last_status)
            
            except Exception as e:
                logger.exception(e)
                clog_last_status.ret_code=500
                clog_last_status.err_desc=clog.DOMUSAPIERROR
                return RagOrchestratorResponse("", "", None, "", None, clog_last_status)
            
            if list_forms and (list_forms.errore or not string.is_null_or_empty_or_whitespace(list_forms.messaggioErrore)):
                clog_last_status.ret_code=200
                clog_last_status.err_desc=clog.DOMUSAPIOKERRORPARAMISTRUE
                return RagOrchestratorResponse("", "", None, "", None, clog_last_status)
            
            if list_forms is None or not list_forms.listaDomande:
                clog_last_status.err_desc=clog.DOMUSAPIOKLISTEMPTY
                return RagOrchestratorResponse("", "", None, "", 
                                            MonitorFormApplication(answer_text=msd_settings.no_form_app_def_answer, 
                                                                    event_type=EventMonitorFormApplication.show_answer_text), 
                                            clog_last_status)
                
            if intent_result.numero_protocollo:
                if not next((domanda for domanda in list_forms.listaDomande if intent_result.numero_protocollo[0] in domanda.numeroProtocollo), None):
                    if len(list_forms.listaDomande) >= 1:
                        return RagOrchestratorResponse("", "", None, "", 
                                                    MonitorFormApplication(answer_text=msd_settings.no_spec_form_app_show_list, 
                                                                            answer_list=[request.model_dump() for request in list_forms.listaDomande],
                                                                            event_type=EventMonitorFormApplication.show_answer_text_and_list), 
                                                    clog_last_status)
                    else: 
                        intent_result.numero_protocollo = None
                        wrong_input = True
                else:
                    user_form_application = next((domanda for domanda in list_forms.listaDomande if domanda.numeroProtocollo == intent_result.numero_protocollo[0]), None)
                    
            if intent_result.numero_domus:
                if not next((domanda for domanda in list_forms.listaDomande if intent_result.numero_domus[0] in domanda.numeroDomus), None):
                    if len(list_forms.listaDomande) >= 1:
                        return RagOrchestratorResponse("", "", None, "", 
                                                    MonitorFormApplication(answer_text=msd_settings.no_spec_form_app_show_list, 
                                                                            answer_list=[request.model_dump() for request in list_forms.listaDomande],
                                                                            event_type=EventMonitorFormApplication.show_answer_text_and_list), 
                                                    clog_last_status)
                    else: 
                        intent_result.numero_domus = None
                        wrong_input = True    
                else:
                   user_form_application = next((domanda for domanda in list_forms.listaDomande if domanda.numeroDomus == intent_result.numero_domus[0]), None)
               
            if (not user_form_application) and (len(list_forms.listaDomande) > 1):
                if string.is_null_or_empty_or_whitespace(request.text_by_card) or len(intent_result.numero_domus) == 0:
                     # save into redis
                    if request.conversation_id:
                        key=redisService.make_key("list",request.conversation_id)
                        redisService.set_to_redis(key, list_forms.model_dump_json())
                    clog_last_status.ret_code=0
                    clog_last_status.err_desc=None
                    return RagOrchestratorResponse("", "", None, "", 
                                                MonitorFormApplication(answer_list=[request.model_dump() for request in list_forms.listaDomande],
                                                    event_type=EventMonitorFormApplication.show_answer_list), clog_last_status)
                else: 
                    user_form_application = next((domanda for domanda in list_forms.listaDomande if domanda.numeroDomus == intent_result.numero_domus[0]), None)
            else:
                if (not user_form_application): 
                    user_form_application = list_forms.listaDomande[0]
                
            if not user_form_application:
                # There are no form application submitted by the client with the specified "numero domus", so the rag will directly response
                return None
                
            clog_params = CLogParams(cf=request.user_fiscal_code, prestazione=tag, 
                                    num_domus=user_form_application.numeroDomus, 
                                    num_prot=user_form_application.numeroProtocollo)
            clog_last_status = CLog(ret_code=0, err_desc=None, id_event=clog_settings.msd_dettagliodomande, params=clog_params)
                
            try:
                form_application_details = await domus.a_get_form_application_details(
                DomusFormApplicationDetailsRequest(user_form_application.numeroDomus, user_form_application.progressivoIstanza, request.token), 
                session, logger)
            
            except ClientResponseError as e:
                logger.exception(e)
                clog_last_status.ret_code=e.code
                clog_last_status.err_desc=clog.DOMUSAPIDETAILERROR
                return RagOrchestratorResponse("", "", None, "", None, clog_last_status)

            except Exception as e:
                logger.exception(e)
                clog_last_status.ret_code=500
                clog_last_status.err_desc=clog.DOMUSAPIDETAILERROR
                return RagOrchestratorResponse("", "", None, "", None, clog_last_status)
                
            if form_application_details and (form_application_details.errore or not string.is_null_or_empty_or_whitespace(form_application_details.messaggioErrore)):
                clog_last_status.ret_code=200
                clog_last_status.err_desc=clog.DOMUSAPIDETAILERRORPARAMISTRUE
                return RagOrchestratorResponse("", "", None, "", None, clog_last_status)
                
            if form_application_details is None:
                clog_last_status.ret_code=200
                clog_last_status.err_desc=clog.DOMUSAPIOKDETAILEMPTY
                return RagOrchestratorResponse("", "", None, "", None, clog_last_status)
                
            # save into redis
            if request.conversation_id and not redis:
                if dettaglioDomus:
                    key=redisService.make_key("dett",request.conversation_id,intent_result.numero_domus[0])
                if dettaglioProto:
                    key=redisService.make_key("dett",request.conversation_id,intent_result.numero_protocollo[0])
                redisService.set_to_redis(key, form_application_details.model_dump_json())
                logger.track_event(event_types.event_track_log_redis_cache,
                               {
                                   "Set_Redis_cache":  json.dumps(form_application_details.model_dump_json(), ensure_ascii=False).encode('utf-8')
                               })
                logger.track_event(event_types.event_track_log_redis_cache,
                               {
                                   "Set_ConvID":  json.dumps(request.conversation_id, ensure_ascii=False).encode('utf-8')
                               })
            
        except Exception as e:
            logger.exception(e)
            clog_last_status.ret_code=500
            clog_last_status.err_desc=clog.DOMUSGENERALAPPLICATIONERROR
            
            return RagOrchestratorResponse("", "", None, "", 
                                            MonitorFormApplication(event_type=EventMonitorFormApplication.application_error),
                                            clog_last_status)
    else:
         # riconoscimento utente autenticato
        if string.is_null_or_empty_or_whitespace(request.user_fiscal_code) or string.is_null_or_empty_or_whitespace(request.token):
            # User not authenticated
            return RagOrchestratorResponse("", "", None, "", 
                                        MonitorFormApplication(event_type=EventMonitorFormApplication.user_not_authenticated))
        # get details from redis
        if carosello:
            list_forms= DomusFormApplicationsByFiscalCodeResponse.model_validate_json(redisCache)
            clog_last_status.ret_code=0
            clog_last_status.err_desc=None
            return RagOrchestratorResponse("", "", None, "", 
                                                MonitorFormApplication(answer_list=[request.model_dump() for request in list_forms.listaDomande],
                                                    event_type=EventMonitorFormApplication.show_answer_list), clog_last_status)

        form_application_details = DomusFormApplicationDetailsResponse.model_validate_json(redisCache)
        logger.track_event(event_types.event_track_log_redis_cache,
                               {
                                   "Redis_cache":  json.dumps(redisCache, ensure_ascii=False).encode('utf-8')
                               })
        logger.track_event(event_types.event_track_log_redis_cache,
                               {
                                   "ConvID":  json.dumps(request.conversation_id, ensure_ascii=False).encode('utf-8')
                               })
        
        clog_params = CLogParams(cf=request.user_fiscal_code, prestazione=tag, 
                                    num_domus=form_application_details.numeroDomus, 
                                    num_prot=form_application_details.numeroProtocollo)
        clog_last_status = CLog(ret_code=0, err_desc=None, id_event=clog_settings.msd_dettagliodomande, params=clog_params)
    
    try:
        if msd_completion_prompt_data == None:
                raise Exception("No enrichment_prompt_data found.")

        domus_result = await language_service.a_get_domus_answer(request, form_application_details.model_dump_json(), msd_completion_prompt_data, logger)

        if domus_result:
            if domus_result.has_answer and domus_result.answer:
                clog_last_status.ret_code=0
                clog_last_status.err_desc=None
                if wrong_input and (request.text_by_card is None or request.text_by_card.strip() == ''):
                    return RagOrchestratorResponse("", "", None, "", MonitorFormApplication(
                        answer_text=f'{msd_settings.no_spec_form_app_show_text} {domus_result.answer}',
                        event_type=EventMonitorFormApplication.show_answer_text),
                                        clog_last_status)
                else:
                    return RagOrchestratorResponse("", "", None, "", MonitorFormApplication(
                        answer_text=domus_result.answer,
                        event_type=EventMonitorFormApplication.show_answer_text),
                                        clog_last_status)
        
        clog_last_status.ret_code=0
        clog_last_status.err_desc=None
        
        if tag_info.id_monitoring_question == EnumMonitorFormApplication.OnlyMonitoringQuestion.value:
            return RagOrchestratorResponse("", "", None, "", 
                                        MonitorFormApplication(answer_text=monitor_form_app.default_answer, event_type=EventMonitorFormApplication.show_answer_text),
                                        clog_last_status)
        
        return await a_do_query(request, completion_prompt_data, language_service, enriched_query, logger, session, 
                                domusData=form_application_details.model_dump_json(),
                                clog=clog_last_status)
        
    except Exception as e:
        logger.exception(e)
        clog_last_status.ret_code=500
        clog_last_status.err_desc=clog.DOMUSGENERALAPPLICATIONERROR
        
        return RagOrchestratorResponse("", "", None, "", 
                                        MonitorFormApplication(event_type=EventMonitorFormApplication.application_error),
                                        clog_last_status)
    
def custom_serializer(obj):
    # Se l'oggetto ha un attributo __dict__, restituiscilo, altrimenti prova a convertirlo in stringa
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    return str(obj)