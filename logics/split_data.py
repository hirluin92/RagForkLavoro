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
from utils.settings import get_storage_settings
from services.storage import (
    a_get_blob_content_from_container,
    get_blob_info_container_and_blobName
)
from services.storage import a_upload_txt_to_blob, a_delete_blob_from_container
from utils.settings import get_storage_settings
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


async def a_split_data_into_chunks(myblob: func.InputStream) -> int: 
    storageSettings = get_storage_settings()
    dest_container = storageSettings.data_source_split_files_container
    blobNameList = myblob.name.split("/")
    filename = blobNameList[-1]
    source_container = blobNameList[0]
    blobNamePath = myblob.name.removeprefix(f"{source_container}/")
    blobfolderPath = blobNamePath.removesuffix(f"/{filename}")
    content = myblob.read().decode("utf-8")
    chunksList = content.split(sep="\r\n\r\n\r\n")
    for index, item in enumerate(chunksList):
        title = filename + f"_chunk{index+1}"
        blobPath = blobfolderPath + f"/{title}"
        await a_upload_txt_to_blob(dest_container, blobPath, item)
    tot = len(chunksList)
    await a_delete_blob_from_container(source_container, blobNamePath)
    return (tot, dest_container)
