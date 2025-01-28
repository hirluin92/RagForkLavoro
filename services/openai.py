import json
from logging import Logger
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from typing import List

from openai import APIConnectionError
from exceptions.custom_exceptions import CustomPromptParameterError
from models.apis.enrichment_query_response import EnrichmentQueryResponse
from models.apis.prompt_editor_response_body import PromptEditorResponseBody
from models.services.llm_context_document import LlmContextContent
from models.services.openai_domus_response import DomusAnswerResponse
from models.services.openai_intent_response import ClassifyIntentResponse
from models.services.openai_rag_response import RagResponse, RagResponseOutputParser
import constants.event_types as event_types
import constants.llm as llm_const
from services.prompt_editor import build_prompt_messages
from utils.settings import get_openai_settings


async def a_generate_embedding_from_text(text: str):
    """
    Generate an embedding from text
    """
    settings = get_openai_settings()
    embeddings = AzureOpenAIEmbeddings(azure_endpoint=settings.embedding_endpoint,
                                       azure_deployment=settings.embedding_deployment_model,
                                       api_key=settings.embedding_key,
                                       api_version=settings.api_version,
                                       check_embedding_ctx_length=False)
    return await embeddings.aembed_query(text)

async def a_get_answer_from_context(question: str,
                                    context: List[LlmContextContent],
                                    prompt_data: PromptEditorResponseBody,
                                    logger: Logger) -> RagResponse:
    """
    Get an answer from a context
    """
    settings = get_openai_settings()

    prompt_messages = build_prompt_messages(prompt_data)

    # Check prompt parameter on prompt messages
    parameters = [f"{{{llm_const.question_variable}}}", f"{{{llm_const.context_variable}}}"]
    check = check_prompt_variable(prompt_messages, parameters)
    if not check:
        err_code = llm_const.status_code_var_compl
        mex = "Invalid completion prompt parameters"
        custom_err = CustomPromptParameterError(mex, err_code)
        raise custom_err
    
    prompt = ChatPromptTemplate.from_messages(prompt_messages)
    
    llm = AzureChatOpenAI(azure_endpoint=settings.completion_endpoint,
                          azure_deployment=settings.completion_deployment_model,
                          api_version=settings.api_version,
                          api_key=settings.completion_key,
                          temperature=prompt_data.model_parameters.temperature,
                          max_tokens=prompt_data.model_parameters.max_length,
                          timeout=30)

    chain = prompt | llm.with_retry() 

    data_to_log = {
        "prompt_messages": json.dumps(prompt_messages, ensure_ascii=False).encode('utf-8'),
        "endpoint": settings.completion_endpoint,
        "deployment": settings.completion_deployment_model,
        "api_version": settings.api_version,
        "temperature": prompt_data.model_parameters.temperature,
        "max_tokens": prompt_data.model_parameters.max_length,
    }
    logger.track_event(event_types.llm_answer_generation_openai_request,
                       data_to_log)

    prompt_and_model_result = await chain.ainvoke({
        llm_const.question_variable: question,
        llm_const.context_variable: context})
    
    logger.track_event(event_types.llm_answer_generation_response_event,
                       {"answer": prompt_and_model_result.json(ensure_ascii=False).encode('utf-8')})
    
    result_content_parser = PydanticOutputParser(
        pydantic_object=RagResponseOutputParser)
    result_content = await result_content_parser.ainvoke(prompt_and_model_result)
    
    return RagResponse(result_content.response,
                       result_content.references,
                   prompt_and_model_result.response_metadata.get("finish_reason", "ND"))


async def a_get_enriched_query(question: str,
                               topic: str,
                               chat_history: str,
                               prompt_data: PromptEditorResponseBody,
                               logger: Logger) -> EnrichmentQueryResponse:
    """
        Contatta il servizio di OpenAI, per migliorare il testo della richiesta.
        Restituisce una EnrichmentQueryResponse, in cui il valore della proprietà EndConversation = true, 
        indica un fallimento nell'operazione
    """
    settings = get_openai_settings()

    prompt_messages = build_prompt_messages(prompt_data)

    # Check prompt parameter on prompt messages
    parameters = [f"{{{llm_const.question_variable}}}", f"{{{llm_const.topic_variable}}}", f"{{{llm_const.chat_variable}}}"]
    check = check_prompt_variable(prompt_messages, parameters)
    if not check:
        err_code = llm_const.status_code_var_enrich
        mex = "Invalid enrichment prompt parameters"
        custom_err = CustomPromptParameterError(mex, err_code)
        raise custom_err
    
    prompt = ChatPromptTemplate.from_messages(prompt_messages)
    
    llm = AzureChatOpenAI(azure_endpoint=settings.completion_endpoint,
                          azure_deployment=settings.completion_deployment_model,
                          api_version=settings.api_version,
                          api_key=settings.completion_key,
                          temperature=prompt_data.model_parameters.temperature,
                          max_tokens=prompt_data.model_parameters.max_length,
                          timeout=30)

    chain = prompt | llm.with_retry() 

    data_to_log = {
        "prompt_messages": json.dumps(prompt_messages, ensure_ascii=False).encode('utf-8'),
        "chat_history": chat_history,
        "question": question,
        "topic": topic
    }

    logger.track_event(event_types.llm_enrichment_request_event, data_to_log)

    result_content = None

    try:
        prompt_and_model_result = await chain.ainvoke({
            llm_const.topic_variable: topic,
            llm_const.question_variable: question,
            llm_const.chat_variable: chat_history 
        })

        logger.track_event(event_types.llm_enrichment_response_event,
                           {"enrichedQuery": prompt_and_model_result.json(ensure_ascii=False).encode('utf-8')})

        result_content_parser = PydanticOutputParser(
            pydantic_object=EnrichmentQueryResponse)
        result_content = await result_content_parser.ainvoke(prompt_and_model_result)
    except APIConnectionError as e:
        logger.exception(f"APIConnectionError: {e}")
        result_content = EnrichmentQueryResponse(standalone_question="",
                                                 end_conversation=True,
                                                 end_conversation_reason=llm_const.default_content_filter_answer)
    except Exception as e:
        if e.status_code == 400:
            logger.exception(e.message)
            result_content = EnrichmentQueryResponse(standalone_question="",
                                                     end_conversation=True,
                                                     end_conversation_reason=llm_const.default_content_filter_answer)
        else:
            raise e

    return result_content


async def a_get_intent_from_enriched_query(question: str, 
                                           prompt_data: PromptEditorResponseBody,
                                            logger: Logger) -> ClassifyIntentResponse:
    settings = get_openai_settings()

    prompt_messages = build_prompt_messages(prompt_data)

    # Check prompt parameter on prompt messages
    parameters = [f"{{{llm_const.question_variable}}}"]
    check = check_prompt_variable(prompt_messages, parameters)
    if not check:
        err_code = llm_const.status_code_var_intent
        mex = "Invalid classify intent prompt parameters"
        custom_err = CustomPromptParameterError(mex, err_code)
        raise custom_err
    
    prompt = ChatPromptTemplate.from_messages(prompt_messages)
    
    llm = AzureChatOpenAI(azure_endpoint=settings.completion_endpoint,
                          azure_deployment=settings.completion_deployment_model,
                          api_version=settings.api_version,
                          api_key=settings.completion_key,
                          temperature=prompt_data.model_parameters.temperature,
                          max_tokens=prompt_data.model_parameters.max_length,
                          timeout=30)

    chain = prompt | llm.with_retry() 

    data_to_log = {
        "prompt_messages": json.dumps(prompt_messages, ensure_ascii=False).encode('utf-8'),
        "endpoint": settings.completion_endpoint,
        "deployment": settings.completion_deployment_model,
        "api_version": settings.api_version,
        "temperature": prompt_data.model_parameters.temperature,
        "max_tokens": prompt_data.model_parameters.max_length,
    }
    logger.track_event(event_types.llm_intent_classification_request,
                       data_to_log)

    prompt_and_model_result = await chain.ainvoke({
        llm_const.question_variable: question})
    
    logger.track_event(event_types.llm_intent_classification_response,
                       {"answer": prompt_and_model_result.json(ensure_ascii=False).encode('utf-8')})
    
    result_content_parser = PydanticOutputParser(
        pydantic_object=ClassifyIntentResponse)
    result_content = await result_content_parser.ainvoke(prompt_and_model_result)

    return result_content


async def a_get_answer_from_domus(question: str, 
                                  practice_detail: str,
                                    prompt_data: PromptEditorResponseBody,
                                    logger: Logger) -> DomusAnswerResponse:
    settings = get_openai_settings()

    prompt_messages = build_prompt_messages(prompt_data)

    # Check prompt parameter on prompt messages
    parameters = [f"{{{llm_const.question_variable}}}"]
    check = check_prompt_variable(prompt_messages, parameters)
    if not check:
        err_code = llm_const.status_code_var_domus
        mex = "Invalid domus answer prompt parameters"
        custom_err = CustomPromptParameterError(mex, err_code)
        raise custom_err
    
    prompt = ChatPromptTemplate.from_messages(prompt_messages)
    
    llm = AzureChatOpenAI(azure_endpoint=settings.completion_endpoint,
                          azure_deployment=settings.completion_deployment_model,
                          api_version=settings.api_version,
                          api_key=settings.completion_key,
                          temperature=prompt_data.model_parameters.temperature,
                          max_tokens=prompt_data.model_parameters.max_length,
                          timeout=30)

    chain = prompt | llm.with_retry() 

    data_to_log = {
        "prompt_messages": json.dumps(prompt_messages, ensure_ascii=False).encode('utf-8'),
        "endpoint": settings.completion_endpoint,
        "deployment": settings.completion_deployment_model,
        "api_version": settings.api_version,
        "temperature": prompt_data.model_parameters.temperature,
        "max_tokens": prompt_data.model_parameters.max_length,
    }
    logger.track_event(event_types.llm_domus_answer_generation_request,
                       data_to_log)

    prompt_and_model_result = await chain.ainvoke({
        llm_const.question_variable: question,
        llm_const.domus_detail_variable: practice_detail})
    
    logger.track_event(event_types.llm_domus_answer_generation_response,
                       {"answer": prompt_and_model_result.json(ensure_ascii=False).encode('utf-8')})
    
    result_content_parser = PydanticOutputParser(
        pydantic_object=DomusAnswerResponse)
    result_content = await result_content_parser.ainvoke(prompt_and_model_result)

    return result_content


def check_prompt_variable(messages, parameters):
    result_string = " | ".join([f"{item[0]} {item[1]}" for item in messages])
    if all(p in result_string for p in parameters):
        return True
    else:
        return False