from dataclasses import asdict
import json
from models.apis.rag_orchestrator_request import Interaction
from services.logging import Logger
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from typing import Any, Dict, List

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
from services.prompt_editor import a_get_prompt_from_resolve_jinja_template_api, build_prompt_messages
from utils.settings import get_openai_settings

# --- SOLUZIONE NON SICURA: SOLO PER SVILUPPO, MAI IN PRODUZIONE ---
# Crea un client HTTPX che non verifica i certificati SSL
# Questo è l'equivalente di verify=False
import httpx  # Assicurati di aver installato httpx: pip install httpx[http2]

unsafe_httpx_async_client = httpx.AsyncClient(verify=False)  # fix locale -> set a True per portare in prod


async def a_generate_embedding_from_text(text: str):
    """
    Generate an embedding from text
    """
    settings = get_openai_settings()
    embeddings = AzureOpenAIEmbeddings(
        azure_endpoint=settings.embedding_endpoint,
        azure_deployment=settings.embedding_deployment_model,
        api_key=settings.embedding_key,
        api_version=settings.api_version,
        check_embedding_ctx_length=False,
        http_async_client=unsafe_httpx_async_client,
    )
    return await embeddings.aembed_query(text)


async def a_get_answer_from_context(
    question: str,
    lang: str,
    context: List[LlmContextContent],
    prompt_data: PromptEditorResponseBody,
    logger: Logger,
    interactions: str,
) -> RagResponse:
    """
    Get an answer from a context
    """
    settings = get_openai_settings()

    context_json_string = [asdict(c) for c in context]

    template_data = {
        "documents": context_json_string,
        "question": question,
        "lang": lang,
        "chat_history": interactions,
    }

    logger.info("Calling Resolve Template API with:")
    logger.info(f"PromptData ID: {getattr(prompt_data, 'id', 'unknown')}")
    logger.info(f"TemplateData: {json.dumps(template_data, ensure_ascii=False)}")

    resolved_jinja_prompt = await a_resolve_template(logger, prompt_data, template_data)

    # Check prompt parameter on prompt data
    fixed_parameters = [llm_const.question_variable, llm_const.context_variable, llm_const.chat_variable]
    value_parameters = [question, context_json_string, interactions]
    variables_indices = check_prompt_variables(resolved_jinja_prompt, fixed_parameters)
    dict_langchain_variables = {fixed_parameters[i]: value_parameters[i] for i in variables_indices}

    prompt_messages = build_prompt_messages(resolved_jinja_prompt)

    prompt = ChatPromptTemplate.from_messages(prompt_messages)

    llm = AzureChatOpenAI(
        azure_endpoint=settings.completion_endpoint,
        azure_deployment=settings.completion_deployment_model,
        api_version=settings.api_version,
        api_key=settings.completion_key,
        temperature=prompt_data.model_parameters.temperature,
        max_tokens=prompt_data.model_parameters.max_length,
        timeout=30,
        http_async_client=unsafe_httpx_async_client,
    )

    chain = prompt | llm.with_retry()

    data_to_log = {
        "prompt_messages": json.dumps(prompt_messages, ensure_ascii=False).encode("utf-8"),
        "endpoint": settings.completion_endpoint,
        "deployment": settings.completion_deployment_model,
        "api_version": settings.api_version,
        "temperature": prompt_data.model_parameters.temperature,
        "max_tokens": prompt_data.model_parameters.max_length,
    }

    logger.track_event(event_types.llm_answer_generation_openai_request, data_to_log)

    try:
        prompt_and_model_result = await chain.ainvoke(dict_langchain_variables)

        logger.track_event(
            event_types.llm_answer_generation_response_event,
            {"answer": prompt_and_model_result.json(ensure_ascii=False).encode("utf-8")},
        )

        result_content_parser = PydanticOutputParser(pydantic_object=RagResponseOutputParser)
        result_content = await result_content_parser.ainvoke(prompt_and_model_result)

    except Exception as err:
        logger.error(err)
        raise err

    return RagResponse(
        result_content.response,
        result_content.references,
        prompt_and_model_result.response_metadata.get("finish_reason", "ND"),
    )


async def a_get_enriched_query(
    question: str, topic: str, chat_history: str, prompt_data: PromptEditorResponseBody, logger: Logger
) -> EnrichmentQueryResponse:
    """
    Contatta il servizio di OpenAI, per migliorare il testo della richiesta.
    Restituisce una EnrichmentQueryResponse, in cui il valore della proprietà EndConversation = true,
    indica un fallimento nell'operazione
    """
    settings = get_openai_settings()

    template_data = {"question": question, "topic": topic, "chat": chat_history}
    resolved_jinja_prompt = await a_resolve_template(logger, prompt_data, template_data)

    # Check prompt parameter on prompt data
    fixed_parameters = [llm_const.question_variable, llm_const.topic_variable, llm_const.chat_variable]
    value_parameters = [question, topic, chat_history]
    variables_indices = check_prompt_variables(resolved_jinja_prompt, fixed_parameters)
    dict_langchain_variables = {fixed_parameters[i]: value_parameters[i] for i in variables_indices}

    prompt_messages = build_prompt_messages(resolved_jinja_prompt)

    prompt = ChatPromptTemplate.from_messages(prompt_messages)

    llm = AzureChatOpenAI(
        azure_endpoint=settings.completion_endpoint,
        azure_deployment=settings.completion_deployment_model,
        api_version=settings.api_version,
        api_key=settings.completion_key,
        temperature=prompt_data.model_parameters.temperature,
        max_tokens=prompt_data.model_parameters.max_length,
        timeout=30,
        http_async_client=unsafe_httpx_async_client,
    )

    chain = prompt | llm.with_retry()

    data_to_log = {
        "prompt_messages": json.dumps(prompt_messages, ensure_ascii=False).encode("utf-8"),
        "chat_history": chat_history,
        "question": question,
        "topic": topic,
    }

    logger.track_event(event_types.llm_enrichment_request_event, data_to_log)

    result_content = None

    try:
        prompt_and_model_result = await chain.ainvoke(dict_langchain_variables)

        logger.track_event(
            event_types.llm_enrichment_response_event,
            {"enrichedQuery": prompt_and_model_result.json(ensure_ascii=False).encode("utf-8")},
        )

        result_content_parser = PydanticOutputParser(pydantic_object=EnrichmentQueryResponse)
        result_content = await result_content_parser.ainvoke(prompt_and_model_result)
    except APIConnectionError as e:
        logger.exception(f"APIConnectionError: {e}")
        result_content = EnrichmentQueryResponse(
            standalone_question="",
            end_conversation=True,
            end_conversation_reason=llm_const.default_content_filter_answer,
        )
    except Exception as err:
        logger.exception(err)
        raise err

    return result_content


async def a_get_intent_from_enriched_query(
    question: str, prompt_data: PromptEditorResponseBody, logger: Logger
) -> ClassifyIntentResponse:
    settings = get_openai_settings()

    template_data = {"question": question}
    resolved_jinja_prompt = await a_resolve_template(logger, prompt_data, template_data)

    # Check prompt parameter on prompt data
    fixed_parameters = [llm_const.question_variable]
    value_parameters = [question]
    variables_indices = check_prompt_variables(resolved_jinja_prompt, fixed_parameters)
    dict_langchain_variables = {fixed_parameters[i]: value_parameters[i] for i in variables_indices}

    prompt_messages = build_prompt_messages(resolved_jinja_prompt)

    prompt = ChatPromptTemplate.from_messages(prompt_messages)

    llm = AzureChatOpenAI(
        azure_endpoint=settings.completion_endpoint,
        azure_deployment=settings.completion_deployment_model,
        api_version=settings.api_version,
        api_key=settings.completion_key,
        temperature=prompt_data.model_parameters.temperature,
        max_tokens=prompt_data.model_parameters.max_length,
        timeout=30,
        http_async_client=unsafe_httpx_async_client,
    )

    chain = prompt | llm.with_retry()

    data_to_log = {
        "prompt_messages": json.dumps(prompt_messages, ensure_ascii=False).encode("utf-8"),
        "endpoint": settings.completion_endpoint,
        "deployment": settings.completion_deployment_model,
        "api_version": settings.api_version,
        "temperature": prompt_data.model_parameters.temperature,
        "max_tokens": prompt_data.model_parameters.max_length,
        "dict_langchain_variables": json.dumps(dict_langchain_variables, ensure_ascii=False).encode("utf-8"),
    }
    logger.track_event(event_types.llm_intent_classification_request, data_to_log)

    try:
        prompt_and_model_result = await chain.ainvoke(dict_langchain_variables)

        logger.track_event(
            event_types.llm_intent_classification_response,
            {"answer": prompt_and_model_result.json(ensure_ascii=False).encode("utf-8")},
        )

        result_content_parser = PydanticOutputParser(pydantic_object=ClassifyIntentResponse)
        result_content = await result_content_parser.ainvoke(prompt_and_model_result)

    except Exception as err:
        logger.exception(err)
        raise err

    return result_content


async def a_get_answer_from_domus(
    question: str, practice_detail: str, prompt_data: PromptEditorResponseBody, logger: Logger
) -> DomusAnswerResponse:
    settings = get_openai_settings()

    template_data = {"question": question, "practice_detail": practice_detail}
    resolved_jinja_prompt = await a_resolve_template(logger, prompt_data, template_data)

    # Check prompt parameter on prompt data
    fixed_parameters = [llm_const.question_variable, llm_const.practice_detail_variable]
    value_parameters = [question, practice_detail]
    variables_indices = check_prompt_variables(resolved_jinja_prompt, fixed_parameters)
    dict_langchain_variables = {fixed_parameters[i]: value_parameters[i] for i in variables_indices}

    prompt_messages = build_prompt_messages(resolved_jinja_prompt)

    prompt = ChatPromptTemplate.from_messages(prompt_messages)

    llm = AzureChatOpenAI(
        azure_endpoint=settings.completion_endpoint,
        azure_deployment=settings.completion_deployment_model,
        api_version=settings.api_version,
        api_key=settings.completion_key,
        temperature=prompt_data.model_parameters.temperature,
        max_tokens=prompt_data.model_parameters.max_length,
        timeout=30,
        http_async_client=unsafe_httpx_async_client,
    )

    chain = prompt | llm.with_retry()

    data_to_log = {
        "prompt_messages": json.dumps(prompt_messages, ensure_ascii=False).encode("utf-8"),
        "endpoint": settings.completion_endpoint,
        "deployment": settings.completion_deployment_model,
        "api_version": settings.api_version,
        "temperature": prompt_data.model_parameters.temperature,
        "max_tokens": prompt_data.model_parameters.max_length,
    }
    logger.track_event(event_types.llm_domus_answer_generation_request, data_to_log)
    try:
        prompt_and_model_result = await chain.ainvoke(dict_langchain_variables)

        logger.track_event(
            event_types.llm_domus_answer_generation_response,
            {"answer": prompt_and_model_result.json(ensure_ascii=False).encode("utf-8")},
        )

        result_content_parser = PydanticOutputParser(pydantic_object=DomusAnswerResponse)
        result_content = await result_content_parser.ainvoke(prompt_and_model_result)

    except Exception as err:
        logger.exception(err)
        raise err

    return result_content


async def a_resolve_template(logger: Logger, prompt_data: PromptEditorResponseBody, template_context: Dict[str, Any]):
    messages = prompt_data.prompt
    prompt_variables = []
    for m in messages:
        resolved_message = await a_get_prompt_from_resolve_jinja_template_api(logger, m.content, template_context)
        logger.track_event(
            event_types.resolve_template_api_response,
            {
                "promptId": prompt_data.id,
                "message_role": m.role,
                "resolved_message": json.dumps(resolved_message.__dict__, ensure_ascii=False).encode("utf-8"),
            },
        )
        m.content = resolved_message.resolved_template
        prompt_variables.extend(resolved_message.parameters)
    prompt_data.parameters = list(set(prompt_variables))

    return prompt_data


def check_prompt_variables(prompt_data: PromptEditorResponseBody, fixed_parameters: list[str]):
    prompt_parameters = prompt_data.parameters
    parameters_indices = []
    parameters_indices = [fixed_parameters.index(item) for item in prompt_parameters if item in fixed_parameters]
    return parameters_indices
