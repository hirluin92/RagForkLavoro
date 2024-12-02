import json
from aiohttp import ClientSession
from tenacity import retry, stop_after_attempt, wait_exponential
from models.configurations.search import SearchSettings
from models.services.search_index_response import SearchIndexResponse
import constants.event_types as event_types
import constants.search as search_constants
from models.apis.rag_orchestrator_request import RagOrchestratorRequest

from services.logging import Logger
from utils.tenacity import retry_if_http_error, wait_for_retry_after_header
import constants.environment as env_const

@retry(
    retry=retry_if_http_error(),
    wait=wait_for_retry_after_header(fallback=wait_exponential(multiplier=1, min=4, max=10)),
    stop=stop_after_attempt(3),
    reraise=True
)
async def a_query(session: ClientSession,
                  request: RagOrchestratorRequest,
                  embedding: list[str],
                  logger: Logger) -> SearchIndexResponse:
    settings = SearchSettings()
    headers = {'Content-Type': 'application/json', 'api-key': settings.key}
    params = {'api-version': settings.api_version}
    #index = settings.index
    k = settings.k
    top = settings.top
    payload = {
        "select": "chunk_id, chunk_text, filename, tags",
        "top": top
    }

    if request.environment == env_const.STAGING: 
        index = settings.index
    elif request.environment == env_const.PRODUCTION:
        index = settings.index_production
    else:
        errMsg = "env_const ({env_const}) not found"
        raise Exception(errMsg.format(env_const = request.environment))

    if len(request.tags) > 0:
        tagsToSearch = ",".join(request.tags)
        filter = "tags/any(t: search.in(t, '{tagsToSearch}'))"
        payload["filter"] = filter.format(tagsToSearch=tagsToSearch)

    if (settings.search_method == search_constants.SEARCH_METHOD_HYBRID
        or settings.search_method == search_constants.SEARCH_METHOD_FULL_TEXT):
        payload["search"] = request.query

    if (settings.search_method == search_constants.SEARCH_METHOD_HYBRID
        or settings.search_method == search_constants.SEARCH_METHOD_VECTOR):
        payload["vectorQueries"] = [
            {"vector": embedding,
             "fields": "chunk_text_vector",
                "kind": "vector",
                  "k": k,
             }]
        
    if settings.semantic_ranking_enabled:
        payload["queryType"] = "semantic"
        payload["semanticConfiguration"] = settings.index_semantic_configuration
        payload["captions"] = "extractive"

    data = json.dumps(payload)
    endpoint: str = settings.endpoint + "/indexes/" + index + "/docs/search"
    async with session.post(endpoint,
                                data=data, 
                                headers=headers, 
                                params=params) as result:
        result_json = await result.json()
        track_event_data = {
            "requestPayload": json.dumps(payload)
        }
        values_to_log: list = result_json.get('value', [])
        index=0
        for value in values_to_log:
            track_event_data["resultDocument_" + str(index).zfill(2)] = json.dumps(value)
            index+=1
        logger.track_event(event_types.search_results_received_event,
                        track_event_data)

        return SearchIndexResponse.from_dict(result_json)