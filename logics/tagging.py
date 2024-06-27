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
from services.storage import a_get_blob_info_for_tagging

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
    url_source = value.data.fileUrl + value.data.fileSasToken
    folders_to_return= []
    metadata_to_return= []
    console_file_id = ""
    try:
        blob_info = await a_get_blob_info_for_tagging(url_source)
        name = blob_info[0]
        metadata = blob_info[1]
        folder_split= name.split('/')
        folder_set = set()
        if len(folder_split) > 1:
            folder_split.pop()
            for value in folder_split:
                folder_set.add(value)
            folders_to_return = list(folder_set)
        if metadata:
            if "id_sql_document" in metadata:
                console_file_id = metadata["id_sql_document"]
                del metadata["id_sql_document"]
            for key, value in metadata.items():
                metadata_to_return.append(key + ':' + value)
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
