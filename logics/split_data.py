import azure.functions as func
from services.logging import Logger
from models.apis.chunking_empty_rows_request_body import (
    ChunkingEmptyRowsRequestBody,
    ValueFromAzAISearch
    )
from models.apis.chunking_empty_rows_response_body import (
    ChunkingEmptyRowsResponseBody,
    ValueToAzAISearch,
    DataToAzAISearch
    )
from services.storage import (
    a_get_blob_content_from_container,
    get_blob_info_container_and_blobName
)
import constants.event_types as event_types


async def a_custom_chunking(req_body: ChunkingEmptyRowsRequestBody,
                   logger: Logger) -> ChunkingEmptyRowsRequestBody:
    values = req_body.values
    results = ChunkingEmptyRowsResponseBody()
    for value in values:
        tags_to_return= await a_split_text_into_chunks(value,logger)
        results.addValue(tags_to_return)
    return results
    
async def a_split_text_into_chunks(value: ValueFromAzAISearch,
                            logger: Logger) -> ValueToAzAISearch:
    recordId = value.recordId
    url_source = value.data.fileUrl + value.data.fileSasToken
    try:
        blob_info = get_blob_info_container_and_blobName(url_source)
        container = blob_info[0]
        blob_filename = blob_info[1]
        blob_text = await a_get_blob_content_from_container(container, blob_filename)
        splittedText = blob_text.split(sep="\r\n\r\n\r\n")
        stripped_chunks = [item.strip() for item in splittedText]
        propertiesDict = {"fileUrl": value.data.fileUrl,
                          "NumberOfChunks": len(stripped_chunks)}
        logger.track_event(event_types.split_data_result, propertiesDict) 
        data_to_return = DataToAzAISearch(stripped_chunks)
        value_to_return = ValueToAzAISearch(recordId, data_to_return, None, None)
        return value_to_return
    except Exception as error:
        error_message = "File processing error. File: {file} | Error: {error}"
        logger.exception(error_message.format(file=url_source, error=str(error)))
        return ValueToAzAISearch(recordId, {},
                                  [{ "message": "Error: " + str(error) }],
                                  None)

