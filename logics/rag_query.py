import json
from typing import List

from aiohttp import ClientSession
from constants import event_types
from models.apis.prompt_editor_response_body import PromptEditorResponseBody
from models.apis.rag_query_response_body import BestDocument, RagQueryResponse
from models.services.llm_context_document import LlmContextContent
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
from models.apis.rag_orchestrator_request import RagOrchestratorRequest


async def a_execute_query(request: RagOrchestratorRequest,
                        prompt_data: PromptEditorResponseBody,
                        logger: Logger,
                        session: ClientSession, 
                        domusData: str = None) -> RagQueryResponse:
    embedding = await openai_generate_embedding_from_text(request.query)
    search_result: SearchIndexResponse = await query_azure_ai_search(
        session, request, embedding, logger)
    search_result_context = build_question_context_from_search(search_result)

    if domusData:
        search_result_context.append(RagContextContent("", domusData, len(search_result_context)+1, "", 100, request.tags[0]))

    if len(search_result_context) == 0:
        return RagQueryResponse(llm_const.default_answer,
                                [],
                                "",
                                [],
                                False,
                                [],
                                [],
                                [])

    response_from_llm = await a_get_response_from_llm(request.query, search_result_context, prompt_data, logger)


    response_for_user = build_response_for_user(response_from_llm, search_result_context)
    response_to_return = response_for_user[0]
    links_to_return = response_for_user[1]
    references_to_return = response_for_user[2]
    finish_reason = response_from_llm.finish_reason
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
                            len(references_to_return) > 0,
                            context_ids_to_return,
                            context_to_return,
                            best_documents_to_return)

def build_question_context_from_search(search_result: SearchIndexResponse) -> list[RagContextContent]:
    """
    Builds the context for the question from the search result.
    The results are ordered by the reranker score in descending order.
    """
    content: list[RagContextContent] = []
    index = 1
    for value in search_result.value:
            score = value.search_rerankerScore
            if score < 0:
                score = value.search_score
            content.append(RagContextContent(value.chunk_id,
                                             value.chunk_text,
                                             index,
                                             value.filename,
                                             score,
                                             ", ".join(value.tags)))
            index += 1

    return sorted(content, key=lambda x: x.score, reverse=True)

async def a_get_response_from_llm(question: str,
                          context: List[RagContextContent],
                          prompt_data: PromptEditorResponseBody,
                          logger) -> RagResponse:

    context_to_send: list[LlmContextContent] = []
    llm_model_id = prompt_data.llm_model
    
    data_to_log = {
        "question": question,
    }
    for index, document in enumerate(context):
        context_to_send_to_append = LlmContextContent(document.chunk, document.reference, document.score) 
        context_to_send.append(context_to_send_to_append)
        data_to_log["context_" + str(index).zfill(2)] = json.dumps(context_to_send_to_append.toJSON(), ensure_ascii=False).encode('utf-8')
    logger.track_event(event_types.llm_answer_generation_request_event, data_to_log)
    
    if llm_model_id == llm_const.mistralai:
        return await mistralai_get_answer_from_context(question,
                                                 context_to_send,
                                                 prompt_data,
                                                 logger)
    else:
        return await openai_get_answer_from_context(question,
                                              context_to_send,
                                              prompt_data,
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
