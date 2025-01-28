import json
from logging import Logger
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_mistralai import ChatMistralAI
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from models.apis.enrichment_query_response import EnrichmentQueryResponse
from models.apis.prompt_editor_response_body import PromptEditorResponseBody
from models.services.llm_context_document import LlmContextContent
from models.services.openai_rag_response import RagResponse, RagResponseOutputParser
import constants.event_types as event_types
from services.prompt_editor import build_prompt_messages
from utils.settings import get_mistralai_settings
from constants import llm as llm_const

async def a_get_answer_from_context(question: str,
                            context: List[LlmContextContent],
                            prompt_data: PromptEditorResponseBody,
                            logger: Logger) -> RagResponse:
    
    settings = get_mistralai_settings()

    prompt_messages = build_prompt_messages(prompt_data)
    prompt = ChatPromptTemplate.from_messages(prompt_messages)
    
    llm = ChatMistralAI(endpoint=settings.endpoint,
                    api_key=settings.key,
                    model_name=settings.model,
                    temperature=prompt_data.model_parameters.temperature,
                    max_tokens=prompt_data.model_parameters.max_length)

    chain = prompt | llm.with_retry() 

    data_to_log = {
            "prompt_messages": json.dumps(prompt_messages, ensure_ascii=False).encode('utf-8'),
            "endpoint": settings.endpoint,
            "deployment": settings.model,
            "temperature": prompt_data.model_parameters.temperature, 
            "max_tokens": prompt_data.model_parameters.max_length,
            "user_question": question
        }

    logger.track_event(event_types.llm_answer_generation_mistralai_request,
                           data_to_log)
    
    prompt_and_model_result = await chain.ainvoke({
        llm_const.question_variable: question,
        llm_const.context_variable: context})
    
    logger.track_event(event_types.llm_answer_generation_response_event,
                           {"answer": prompt_and_model_result.json(ensure_ascii=False).encode('utf-8')})

    result_content_parser = PydanticOutputParser(pydantic_object=RagResponseOutputParser)
    result_content = await result_content_parser.ainvoke(prompt_and_model_result)

    return RagResponse(result_content.response,
                       result_content.references,
                       prompt_and_model_result.response_metadata.get("finish_reason", "ND"))


async def a_get_enriched_query(query: str,
                       topic: str,
                       chat_history: str,
                       prompt_data: PromptEditorResponseBody,
                       logger: Logger) -> EnrichmentQueryResponse:
    """
        Contatta il servizio di MistralAI, per migliorare il testo della richiesta.
        Restituisce una EnrichmentQueryResponse, in cui il valore della proprietà EndConversation = true, 
        indica un fallimento nell'operazione
    """
    settings = get_mistralai_settings()

    prompt_messages = build_prompt_messages(prompt_data)
    prompt = ChatPromptTemplate.from_messages(prompt_messages)
    
    llm = ChatMistralAI(endpoint=settings.endpoint,
                    api_key=settings.key,
                    model_name=settings.model,
                    temperature=prompt_data.model_parameters.temperature,
                    max_tokens=prompt_data.model_parameters.max_length,
                    timeout=30)

    chain = prompt | llm.with_retry() 

    data_to_log = {
        "prompt_messages": json.dumps(prompt_messages, ensure_ascii=False).encode('utf-8'),
        "chat_history": chat_history,
        "question": query,
        "topic": topic
    }
    
    logger.track_event(event_types.llm_enrichment_request_event, data_to_log)
    
    prompt_and_model_result = await chain.ainvoke({
        llm_const.topic_variable: topic,
        llm_const.question_variable: query,
        llm_const.chat_variable: chat_history 
    })
    
    logger.track_event(event_types.llm_enrichment_response_event,
                           {"enrichedQuery": prompt_and_model_result.json(ensure_ascii=False).encode('utf-8')})
    
    result_content_parser = PydanticOutputParser(pydantic_object=EnrichmentQueryResponse)
    result_content = await result_content_parser.ainvoke(prompt_and_model_result)

    return result_content