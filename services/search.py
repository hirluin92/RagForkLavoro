import json
from aiohttp import ClientSession
from tenacity import retry, stop_after_attempt, wait_exponential
from models.configurations.search import SearchSettings
from models.services.search_index_response import SearchIndexResponse
import constants.event_types as event_types

from services.logging import Logger
from utils.tenacity import retry_if_http_error, wait_for_retry_after_header


@retry(
    retry=retry_if_http_error(),
    wait=wait_for_retry_after_header(fallback=wait_exponential(multiplier=1, min=4, max=10)),
    stop=stop_after_attempt(3),
    reraise=True
)
async def a_query(session: ClientSession,
                  question: str,
                  embedding: list[str],
                  tags: list[str],
                  logger: Logger) -> SearchIndexResponse:
    settings = SearchSettings()
    headers = {'Content-Type': 'application/json', 'api-key': settings.key}
    params = {'api-version': settings.api_version}
    index = settings.index
    k = settings.k
    top = settings.top
    payload = {
        "search": question,
        "select": "chunk_id, chunk_text, filename, tags",
        "queryType": "semantic",
        "vectorQueries": [
            {"vector": embedding,
             "fields": "chunk_text_vector",
                "kind": "vector",
                  "k": k,
             }],
        "semanticConfiguration": settings.index_semantic_configuration,
        "captions": "extractive",
        "top": top
    }
    if len(tags) > 0:
        tagsToSearch = ",".join(tags)
        filter = "tags/any(t: search.in(t, '{tagsToSearch}'))"
        payload["filter"] = filter.format(tagsToSearch=tagsToSearch)

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