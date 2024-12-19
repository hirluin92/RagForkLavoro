import json
from logging import Logger
from typing import Optional
from aiohttp import ClientSession
from tenacity import retry, stop_after_attempt, wait_exponential
from constants import event_types
from models.apis.prompt_editor_response_body import PromptEditorResponseBody
from models.apis.rag_orchestrator_request import PromptEditorCredential
from models.configurations.prompt import PromptSettings
from utils.tenacity import retry_if_http_error, wait_for_retry_after_header
from constants import llm as llm_const


@retry(
    retry=retry_if_http_error(),
    wait=wait_for_retry_after_header(fallback=wait_exponential(multiplier=1, min=4, max=10)),
    stop=stop_after_attempt(3),
    reraise=True
)
async def a_get_response_from_api_prompt_editor(promptId: str,
                                                logger: Logger,
                                                session: ClientSession,
                                                version: Optional[str] = None) -> PromptEditorResponseBody:
    
    settings = PromptSettings()
    endpoint = settings.editor_endpoint + f"/{promptId}"
    if(version != None and version != ""):
        endpoint = settings.editor_endpoint + f"/{promptId}/{version}"   
    headers = {'Content-Type': 'application/json', 'x-functions-key': settings.editor_api_key}
    async with session.get(endpoint,
                            headers=headers) as result:
        result_json = await result.json()
        result_json_string = json.dumps(result_json)
        track_event_data = {
            "request_endpoint": endpoint,
            "promptID": promptId,
            "prompt_version": version,
            "response": result_json_string
        }
        logger.track_event(event_types.prompt_editor_result,
                        track_event_data)

        return PromptEditorResponseBody.from_dict(result_json)

async def a_get_enrichment_prompt_data(prompt_editor: list[PromptEditorCredential],
                                       logger: Logger,
                                       session: ClientSession) -> PromptEditorResponseBody:
    settings = PromptSettings()
    prompt_data = next((p for p in prompt_editor if p.type == llm_const.enrichment), None)
    if(prompt_data != None):
        promptId = prompt_data.id
        version = prompt_data.version
    else:
        promptId = settings.enrichment_default_id
        version = settings.enrichment_default_version
    result = await a_get_response_from_api_prompt_editor(promptId, logger, session,  version)
    return result

async def a_get_completion_prompt_data(prompt_editor: list[PromptEditorCredential],
                                logger: Logger,
                                session: ClientSession)-> PromptEditorResponseBody:
    settings = PromptSettings()
    prompt_data = next((p for p in prompt_editor if p.type == llm_const.completion), None)
    if(prompt_data != None):
        promptId = prompt_data.id
        version = prompt_data.version
    else:
        promptId = settings.completion_default_id
        version = settings.completion_default_version
    result = await a_get_response_from_api_prompt_editor(promptId, logger, session, version)
    return result

def build_prompt_messages(prompt_data: PromptEditorResponseBody):
    messages = prompt_data.prompt
    tuple_messages = [(m.role, m.content) for m in messages]
    return tuple_messages
