from logging import Logger
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from typing import List
from models.apis.enrichment_query_response import EnrichmentQueryResponse
from models.services.llm_context_document import LlmContextContent
from models.services.openai_rag_response import RagResponse, RagResponseOutputParser
import constants.event_types as event_types
import constants.llm as llm_const
import constants.prompt as prompt_const
from services.storage import a_get_blob_content_from_container
from utils.settings import get_app_settings, get_openai_settings, get_storage_settings

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
                            system_prompt: str,
                            system_links_prompt: str,
                            user_prompt:str,
                            logger: Logger) -> RagResponse:
    """
    Get an answer from a context
    """
    settings = get_openai_settings()
    doc_search_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ]
    )
    llm = AzureChatOpenAI(azure_endpoint = settings.completion_endpoint,
                          azure_deployment = settings.completion_deployment_model,
                          api_version = settings.api_version,
                          api_key = settings.completion_key,
                          temperature = settings.completion_temperature, 
                          max_tokens = settings.completion_tokens,
                          timeout=30)

    chain = (
        doc_search_prompt  # Passes the input variables above to the prompt template
        | llm.with_retry()  # Passes the finished prompt to the LLM
    )

    data_to_log = {
            "endpoint": settings.completion_endpoint,
            "deployment": settings.completion_deployment_model,
            "api_version": settings.api_version,
            "temperature": settings.completion_temperature, 
            "max_tokens": settings.completion_tokens
        }

    logger.track_event(event_types.llm_answer_generation_openai_request,
                           data_to_log)

    prompt_and_model_result = await chain.ainvoke(
        {
            "system_links_prompt": system_links_prompt,
            "question": question,
            "context": context
        })
    
    logger.track_event(event_types.llm_answer_generation_response_event,
                           {"answer": prompt_and_model_result.json()})

    result_content_parser = PydanticOutputParser(pydantic_object=RagResponseOutputParser)
    result_content = await result_content_parser.ainvoke(prompt_and_model_result)

    return RagResponse(result_content.response,
                       result_content.references,
                       prompt_and_model_result.response_metadata.get("finish_reason", "ND"))

async def a_get_enriched_query(query: str,
                       topic: str,
                       chat_history: str,
                       logger: Logger) -> EnrichmentQueryResponse:
    """
        Contatta il servizio di OpenAI, per migliorare il testo della richiesta.
        Restituisce una EnrichmentQueryResponse, in cui il valore della proprietà EndConversation = true, 
        indica un fallimento nell'operazione
    """
    # Lettura parametri di configurazione
    app_settings = get_app_settings()
    openai_settings = get_openai_settings()
    storage_settings = get_storage_settings()

    # Caricamento delle risorse
    enrichment_prompt_template = await a_get_blob_content_from_container(storage_settings.prompt_files_container,
                                                        prompt_const.ENRICHMENT_SYSTEM)
    user_message_template = await a_get_blob_content_from_container(storage_settings.prompt_files_container,
                                                        prompt_const.ENRICHMENT_USER)
    # Costruzione chain
    prompt = ChatPromptTemplate.from_messages([
        ("system", enrichment_prompt_template),
        ("user", user_message_template)
    ])
    
    llm = AzureChatOpenAI(azure_endpoint = openai_settings.completion_endpoint,
                          azure_deployment = openai_settings.completion_deployment_model,
                          api_version = openai_settings.api_version,
                          api_key = openai_settings.completion_key,
                          temperature = openai_settings.completion_temperature, 
                          max_tokens = openai_settings.completion_tokens)
    
    chain = prompt | llm.with_retry() 

    data_to_log = {
        "systemPrompt": enrichment_prompt_template,
        "humanPrompt": user_message_template,
        "chat_history": chat_history,
        "question": query,
        "topic": topic,
        "enrichment_by_topic_enabled": app_settings.enrichment_by_topic_enabled
    }
    
    logger.track_event(event_types.llm_enrichment_request_event, data_to_log)

    topic_to_chain = ""
    if app_settings.enrichment_by_topic_enabled:
        topic_to_chain = topic

    result_content = None

    try:
        prompt_and_model_result =  await chain.ainvoke({
        "topic": topic_to_chain,
        "chat_history": chat_history,
        "question": query
        })
        
        logger.track_event(event_types.llm_enrichment_response_event,
                            {"enrichedQuery": prompt_and_model_result.json()})

        result_content_parser = PydanticOutputParser(pydantic_object=EnrichmentQueryResponse)
        result_content = await result_content_parser.ainvoke(prompt_and_model_result)
    except Exception as e:
        if e.status_code == 400:
            logger.exception(e.message)
            result_content = EnrichmentQueryResponse(standalone_question="",
                                                     end_conversation=True,
                                                     end_conversation_reason=llm_const.default_content_filter_answer)
        else:
            raise e

    return result_content