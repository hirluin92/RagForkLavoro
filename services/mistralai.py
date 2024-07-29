import json
from logging import Logger
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_mistralai import ChatMistralAI
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from models.apis.enrichment_query_response import EnrichmentQueryResponse
from models.services.openai_rag_context_content import RagContextContent
from models.services.openai_rag_response import RagResponse, RagResponseOutputParser
import constants.event_types as event_types
from services.storage import a_get_blob_content_from_container
import constants.prompt as prompt_const
from utils.settings import get_mistralai_settings, get_storage_settings

async def a_get_answer_from_context(question: str,
                            context: List[RagContextContent],
                            system_prompt: str,
                            system_links_prompt: str,
                            user_prompt:str,
                            logger: Logger) -> RagResponse:
    settings = get_mistralai_settings()
    doc_search_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ]
    )
    llm = ChatMistralAI(endpoint=settings.endpoint,
                        api_key=settings.key,
                        model_name=settings.model,
                        temperature=settings.temperature,
                        max_tokens=settings.tokens)

    chain = (
        doc_search_prompt  # Passes the input variables above to the prompt template
        | llm.with_retry()   # Passes the finished prompt to the LLM
    )

    data_to_log = {
            "endpoint": settings.endpoint,
            "deployment": settings.model,
            "temperature": settings.temperature, 
            "max_tokens": settings.tokens
        }

    logger.track_event(event_types.llm_answer_generation_mistralai_request,
                           data_to_log)
    
    prompt_and_model_result = await chain.ainvoke({
        "system_links_prompt": system_links_prompt,
        "question": question,
        "context": context})
    logger.track_event(event_types.llm_answer_generation_response_event,
                           {"answer": prompt_and_model_result.json()})

    result_content_parser = PydanticOutputParser(pydantic_object=RagResponseOutputParser)
    result_content = await result_content_parser.ainvoke(prompt_and_model_result)

    return RagResponse(result_content.response,
                       result_content.references,
                       prompt_and_model_result.response_metadata.get("finish_reason", "ND"))

async def a_get_enriched_query(query: str,
                       tags: list[str],
                       chat_history: str,
                       logger: Logger) -> EnrichmentQueryResponse:
    """
        Contatta il servizio di MistralAI, per migliorare il testo della richiesta.
        Restituisce una EnrichmentQueryResponse, in cui il valore della proprietà EndConversation = true, 
        indica un fallimento nell'operazione
    """
    # Lettura parametri di configurazione
    storage_settings = get_storage_settings()
    mistralai_settings = get_mistralai_settings()

        # Caricamento delle risorse
    enrichment_prompt_template = await a_get_blob_content_from_container(storage_settings.prompt_files_container,
                                                        prompt_const.ENRICHMENT_SYSTEM)
    user_message_template = await a_get_blob_content_from_container(storage_settings.prompt_files_container,
                                                        prompt_const.ENRICHMENT_USER)
    tags_map = json.loads(await a_get_blob_content_from_container(storage_settings.prompt_files_container,
                                                        prompt_const.TAGS_MAPPING))
    
    if not enrichment_prompt_template or not user_message_template or not tags: 
        raise Exception("Cannot read templates")

    # Recupero il topic
    if tags and len(tags) > 0:
        topic  = tags_map.get(tags[0])

    # Costruzione chain
    prompt = ChatPromptTemplate.from_messages([
        ("system", enrichment_prompt_template),
        ("user", user_message_template)
    ])
    
    llm = ChatMistralAI(endpoint=mistralai_settings.endpoint,
                    api_key=mistralai_settings.key,
                    model_name=mistralai_settings.model,
                    temperature=mistralai_settings.temperature,
                    max_tokens=mistralai_settings.tokens)

    chain = prompt | llm.with_retry() 

    data_to_log = {
        "systemPrompt": enrichment_prompt_template,
        "humanPrompt": user_message_template,
        "chat_history": chat_history,
        "question": query,
        "topic": topic
    }
    
    logger.track_event(event_types.llm_enrichment_request_event, data_to_log)
    
    prompt_and_model_result = await chain.ainvoke({
        "topic": topic,
        "chat_history": chat_history,
        "question": query
    })
    
    logger.track_event(event_types.llm_enrichment_response_event,
                           {"enrichedQuery": prompt_and_model_result.json()})
    
    result_content_parser = PydanticOutputParser(pydantic_object=EnrichmentQueryResponse)
    result_content = await result_content_parser.ainvoke(prompt_and_model_result)

    return result_content