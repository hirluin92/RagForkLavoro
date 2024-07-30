from models.apis.tagging_request_body import (
    TaggingRequestBody,
    ValueFromAzAISearch,
    )
from models.apis.tagging_response_body import (
    DataToAzAISearch,
    TaggingResponseBody,
    ValueToAzAISearch,
)
from services.logging import Logger
from services.storage import a_get_blobName_and_metadata_for_tagging, a_create_metadata_on_blob
import uuid

ID_SQL_DOCUMENT= "id_sql_document"
TAGS_PRESTAZIONE = "tags_prestazione"

async def a_get_files_tags(req_body: TaggingRequestBody,
                   logger: Logger) -> TaggingResponseBody:
    values = req_body.values
    results = TaggingResponseBody()
    for value in values:
        tags_to_return= await a_get_tags_from_blob_info(value,logger)
        results.addValue(tags_to_return)
    return results

async def a_get_tags_from_blob_info(value: ValueFromAzAISearch,
                            logger: Logger) -> ValueToAzAISearch:
    recordId = value.recordId
    blob_storage_path = value.data.fileUrl
    #sas_token = value.data.fileSasToken
    url_source = blob_storage_path #+ sas_token
    try:
        folders_to_return = await a_get_folders_name(url_source)
        tags_prestazione_to_add = ",".join(folders_to_return)
        await a_create_metadata_on_blob(
            url_source, TAGS_PRESTAZIONE, tags_prestazione_to_add)

        console_file_id = await a_get_or_create_console_file_id(url_source)
        metadata_to_return = await a_get_all_blob_metadata(url_source)
        data_to_return = DataToAzAISearch(folders_to_return,
                                           metadata_to_return,
                                            console_file_id)
        value_to_return = ValueToAzAISearch(recordId, data_to_return, None, None)
        return value_to_return
    except Exception as error:
        error_message = "File processing error. File: {file} | Error: {error}"
        logger.exception(error_message.format(file=url_source, error=str(error)))
        return ValueToAzAISearch(recordId, {},
                                  [{ "message": "Error: " + str(error) }],
                                  None)

async def a_get_folders_name(url_source: str) -> list[str]:
    (blobName, metadata) = await a_get_blobName_and_metadata_for_tagging(url_source)
    folders_to_return= []
    folder_split= blobName.split('/')
    folder_set = set()
    if len(folder_split) > 1:
        folder_split.pop()
        for value in folder_split:
            folder_set.add(value)
        folders_to_return = list(folder_set)
    return folders_to_return

async def a_get_or_create_console_file_id(url_source: str) -> str:
    (blobName, metadata) = await a_get_blobName_and_metadata_for_tagging(url_source)
    metadataKey = ID_SQL_DOCUMENT
    metadataValue = str(uuid.uuid4())
    if metadataKey in metadata:
        console_file_id = metadata[ID_SQL_DOCUMENT]
    else:
        await a_create_metadata_on_blob(url_source, metadataKey, metadataValue)
        console_file_id = metadataValue
    return console_file_id

async def a_get_all_blob_metadata(url_source:str) -> list[str]:
    blob_info = await a_get_blobName_and_metadata_for_tagging(url_source)
    updatedMetadata = blob_info[1]
    metadata_to_return= []
    for key, value in updatedMetadata.items():
        metadata_to_return.append(key + ':' + value)
    return metadata_to_return