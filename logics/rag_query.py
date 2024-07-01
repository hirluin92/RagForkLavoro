import json
from typing import List

from aiohttp import ClientSession
from constants import event_types
from models.apis.rag_query_response_body import BestDocument, RagQueryResponse
from models.services.openai_rag_context_content import RagContextContent
from models.services.openai_rag_response import RagResponse
from models.services.search_index_response import SearchIndexResponse
from services.logging import Logger
from services.mistralai import (
    a_get_answer_from_context as mistralai_get_answer_from_context)
from services.openai import (
    a_generate_embedding_from_text as openai_generate_embedding_from_text,
    a_get_answer_from_context as openai_get_answer_from_context)
from services.search import a_query as query_azure_ai_search
import constants.llm as llm_const
import constants.prompt as prompt_const
from services.storage import a_get_blob_content_from_container
from utils.settings import get_storage_settings


async def a_execute_query(llm_model_id: str,
                  question: str,
                  tags: list[str],
                  logger: Logger,
                  session: ClientSession) -> RagQueryResponse:
    embedding = await openai_generate_embedding_from_text(question)
    search_result: SearchIndexResponse = await query_azure_ai_search(
        session, question, embedding, tags, logger)
    search_result_context = build_question_context_from_search(search_result)

    if len(search_result_context) == 0:
        return RagQueryResponse(llm_const.default_answer,
                                [],
                                "",
                                [],
                                False,
                                [],
                                [],
                                [])
    response_from_llm = await a_get_response_from_llm(
        llm_model_id, question, search_result_context, logger)
    finish_reason = response_from_llm.finish_reason
    response_for_user = build_response_for_user(
        response_from_llm, search_result_context)
    response_to_return = response_for_user[0]
    links_to_return = response_for_user[1]
    references_to_return = response_for_user[2]

    context_ids_to_return = []
    context_to_return = []
    best_documents_to_return = []
    for item in search_result_context:
        context_ids_to_return.append(item.chunk_id)
        context_to_return.append(item.chunk)
        best_document = BestDocument(
            item.chunk_id,
            "",
            item.filename,
            item.tags,
            "",
            item.score,
            item.chunk,
            item.reference
        )
        best_documents_to_return.append(best_document)
    return RagQueryResponse(response_to_return,
                            references_to_return,
                            finish_reason,
                            links_to_return,
                            len(context_ids_to_return) > 0,
                            context_ids_to_return,
                            context_to_return,
                            best_documents_to_return)

def build_question_context_from_search(search_result: SearchIndexResponse,
                                       reranker_threshold: int = 0) -> list[RagContextContent]:
    """
    Builds the context for the question from the search result.
    The results are ordered by the reranker score in descending order.
    """
    content: list[RagContextContent] = []
    index = 1
    for value in search_result.value:
        if value.search_rerankerScore > reranker_threshold:
            content.append(RagContextContent(value.chunk_id,
                                             value.chunk_text,
                                             index,
                                             value.filename,
                                             value.search_captions[0].text,
                                             value.search_rerankerScore,
                                             ", ".join(value.tags)))
            index += 1

    return sorted(content, key=lambda x: x.score, reverse=True)

async def a_get_response_from_llm(llm_model_id: str,
                          question: str,
                          context: List[RagContextContent],
                          logger) -> RagResponse:
    storageSettings = get_storage_settings()
    system_prompt = await a_get_blob_content_from_container(storageSettings.prompt_files_container,
                                                        prompt_const.ANSWER_GENERATION_SYSTEM_PROMPT)
    user_prompt = await a_get_blob_content_from_container(storageSettings.prompt_files_container,
                                                        prompt_const.ANSWER_GENERATION_USER_PROMPT)
    
    data_to_log = {
        "systemPrompt": system_prompt,
        "humanPrompt": user_prompt,
        "question": question,
    }
    for index, document in enumerate(context):
        data_to_log["context_" + str(index).zfill(2)] = json.dumps(document.toJSON())

    logger.track_event(event_types.llm_answer_generation_request_event, data_to_log)

    if llm_model_id == llm_const.mistralai:
        return await mistralai_get_answer_from_context(question,
                                                 context,
                                                 system_prompt,
                                                 user_prompt,
                                                 logger)
    else:
        return await openai_get_answer_from_context(question,
                                              context,
                                              system_prompt,
                                              user_prompt, 
                                              logger)

def build_response_for_user(rag_response: RagResponse,
                            context: list[RagContextContent]) -> tuple[str, list[str], list[int]]:
    if len(rag_response.references) > 0:
        documents: list[str] = []
        for reference in rag_response.references:
            filename_to_add = next(
                (x for x in context if x.reference == reference), None)
            if filename_to_add:
                documents.append(filename_to_add.filename)
        if len(documents) > 0 and len(documents) == len(rag_response.references):
            return (rag_response.response, documents, rag_response.references)
        elif len(documents) != len(rag_response.references):
            errMsg = """Bad answer from llm. 
            Number of references:  {references}. 
            Number of context documents: {documents}"""
            raise Exception(errMsg.format(references = len(rag_response.references),
                                          documents = len(documents)))

    return (llm_const.default_answer, [], [])
