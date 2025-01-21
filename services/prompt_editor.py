import json
from logging import Logger
from typing import Optional, Tuple
from aiohttp import ClientSession
from tenacity import retry, stop_after_attempt, wait_exponential
from constants import event_types
from models.apis.prompt_editor_response_body import PromptEditorResponseBody
from models.apis.rag_orchestrator_request import PromptEditorCredential
from models.configurations.prompt import PromptSettings
from utils.tenacity import retry_if_http_error, wait_for_retry_after_header
from constants import llm as llm_const
from models.apis.prompt_editor_request_body import PromptEditorRequest
from constants import misc as misc_const
from dataclasses import asdict

@retry(
    retry=retry_if_http_error(),
    wait=wait_for_retry_after_header(
        fallback=wait_exponential(multiplier=1, min=4, max=10)),
    stop=stop_after_attempt(3),
    reraise=True
)
async def a_get_response_from_prompt_retrieval_api(promptId: str,
                                                   logger: Logger,
                                                   session: ClientSession,
                                                   version: Optional[str] = None) -> PromptEditorResponseBody:

    settings = PromptSettings()
    endpoint = settings.editor_endpoint + f"/{promptId}"
    if (version != None and version != ""):
        endpoint = settings.editor_endpoint + f"/{promptId}/{version}"
    # headers = {'Content-Type': 'application/json',
    #            'x-functions-key': settings.editor_api_key}
    headers = {misc_const.HTTP_HEADER_CONTENT_TYPE_NAME: misc_const.HTTP_HEADER_CONTENT_TYPE_JSON_VALUE,
               misc_const.HTTP_HEADER_FUNCTION_KEY_NAME: settings.editor_api_key}
    async with session.get(endpoint,
                           headers=headers) as result:
        result_json = await result.json()
        result_json_string = json.dumps(result_json)
        track_event_data = {
            "request_endpoint": endpoint,
            "prompt_id": promptId,
            "prompt_version": version,
            "response": result_json_string
        }
        logger.track_event(event_types.get_prompts_result,
                           track_event_data)

        return PromptEditorResponseBody.from_dict(result_json)


@retry(
    retry=retry_if_http_error(),
    wait=wait_for_retry_after_header(
        fallback=wait_exponential(multiplier=1, min=4, max=10)),
    stop=stop_after_attempt(3),
    reraise=True
)
# async def a_get_response_from_prompts_api(logger: Logger,
#                                           session: ClientSession,
#                                           enrichment_prompt_id: str,
#                                           completion_prompt_id: str,
#                                           enrichment_version: Optional[str] = None,
#                                           completion_version: Optional[str] = None) -> Tuple[PromptEditorResponseBody, PromptEditorResponseBody]:

async def a_get_response_from_prompts_api(logger: Logger,
                                          session: ClientSession,
                                          payloads : list[PromptEditorRequest]) -> Tuple[PromptEditorResponseBody, PromptEditorResponseBody]:

    settings = PromptSettings()
    endpoint = settings.editor_endpoint
    data = payloads.toJSON()

    track_event_data = [asdict(payload) for payload in payloads]
    logger.track_event(event_types.prompts_api_result_request, track_event_data)
    
    headers = {misc_const.HTTP_HEADER_CONTENT_TYPE_NAME: misc_const.HTTP_HEADER_CONTENT_TYPE_JSON_VALUE,
               misc_const.HTTP_HEADER_FUNCTION_KEY_NAME: settings.editor_api_key}
    async with session.post(endpoint,
                            data=data,
                            headers=headers) as result:
        result_json = await result.json()
        result_json_string = json.dumps(result_json)
        track_event_data = {
            "request_endpoint": endpoint,
            "response": result_json_string
        }
        logger.track_event(event_types.prompts_api_result_response, track_event_data)

        #return (PromptEditorResponseBody.from_dict(result_json[0]), PromptEditorResponseBody.from_dict(result_json[1]))
        return result_json


async def a_get_enrichment_prompt_data(prompt_editor: list[PromptEditorCredential],
                                       logger: Logger,
                                       session: ClientSession) -> PromptEditorResponseBody:
    settings = PromptSettings()
    prompt_data = next(
        (p for p in prompt_editor if p.type == llm_const.enrichment), None)
    if (prompt_data != None):
        promptId = prompt_data.id
        version = prompt_data.version
    else:
        promptId = settings.enrichment_default_id
        version = settings.enrichment_default_version
    result = await a_get_response_from_prompt_retrieval_api(promptId, logger, session,  version)
    return result


async def a_get_completion_prompt_data(prompt_editor: list[PromptEditorCredential],
                                       logger: Logger,
                                       session: ClientSession) -> PromptEditorResponseBody:
    settings = PromptSettings()
    prompt_data = next(
        (p for p in prompt_editor if p.type == llm_const.completion), None)
    if (prompt_data != None):
        promptId = prompt_data.id
        version = prompt_data.version
    else:
        promptId = settings.completion_default_id
        version = settings.completion_default_version
    result = await a_get_response_from_prompt_retrieval_api(promptId, logger, session, version)
    return result


async def a_get_prompts_data(prompt_editor: list[PromptEditorCredential],
                             logger: Logger,
                             session: ClientSession) -> PromptEditorResponseBody:
    settings = PromptSettings()
    
    payload = []

    enrichment_prompt_data = next(
        (p for p in prompt_editor if p.type == llm_const.enrichment), None)
    payload.append(PromptEditorRequest(
            enrichment_prompt_data.id if enrichment_prompt_data != None else settings.enrichment_default_id,
            enrichment_prompt_data.version if enrichment_prompt_data != None else settings.enrichment_default_version,
        llm_const.enrichment
        ))
    
    completion_prompt_data = next(
        (p for p in prompt_editor if p.type == llm_const.completion), None)
    payload.append(PromptEditorRequest(
            completion_prompt_data.id if completion_prompt_data != None else settings.completion_default_id,
            completion_prompt_data.version if completion_prompt_data != None else settings.completion_default_version,
        llm_const.completion
        ))

    msd_intent_recognition_prompt_data = next(
        (p for p in prompt_editor if p.type == llm_const.msd_intent_recognition), None)
    payload.append(PromptEditorRequest(
            msd_intent_recognition_prompt_data.id if msd_intent_recognition_prompt_data != None else settings.msd_intent_recognition_default_id,
            msd_intent_recognition_prompt_data.version if msd_intent_recognition_prompt_data != None else settings.msd_intent_recognition_default_version,
        llm_const.msd_intent_recognition
        ))
    
    msd_completion_prompt_data = next(
        (p for p in prompt_editor if p.type == llm_const.msd_completion), None)
    payload.append(PromptEditorRequest(
            msd_completion_prompt_data.id if msd_completion_prompt_data != None else settings.msd_completion_default_id,
            msd_completion_prompt_data.version if msd_completion_prompt_data != None else settings.msd_completion_default_version,
        llm_const.msd_completion
        ))
    
    listPrompt = await a_get_response_from_prompts_api(logger, session, payload)

    return (
        PromptEditorResponseBody.from_dict(next(p for p in listPrompt if p.type == llm_const.enrichment), None), 
        PromptEditorResponseBody.from_dict(next(p for p in listPrompt if p.type == llm_const.completion), None),
        PromptEditorResponseBody.from_dict(next(p for p in listPrompt if p.type == llm_const.msd_intent_recognition), None),
        PromptEditorResponseBody.from_dict(next(p for p in listPrompt if p.type == llm_const.msd_completion), None),
        )


def build_prompt_messages(prompt_data: PromptEditorResponseBody):
    messages = prompt_data.prompt
    tuple_messages = [(m.role, m.content) for m in messages]
    return tuple_messages
