import azure.functions as func 
from models.apis.movefiles_request_body import MoveFilesRequestBody, ValueFromAzAISearch
from models.apis.movefiles_response_body import (
    DataToAzAISearch,
    MoveFilesResponseBody,
    ValueToAzAISearch
    )
from services.logging import LoggerBuilder
import constants.event_types as event_types
from services.storage import get_blob_info_for_move, a_move_blob
from utils.settings import get_storage_settings


async def a_move_all_data_response(req_body: MoveFilesRequestBody, context: func.Context) -> MoveFilesResponseBody:
    result = MoveFilesResponseBody()
    for value in req_body.values:
        movedRecord = await a_move_item(value, context)
        result.addValue(movedRecord)
    return result
    
async def a_move_item(item: ValueFromAzAISearch, context: func.Context) -> ValueToAzAISearch:
    with LoggerBuilder(__name__, context) as logger:
        fileUrl =  item.data.fileUrl
        fileSasToken = item.data.fileSasToken
        url_source = fileUrl + fileSasToken
        blob_from_info = get_blob_info_for_move(url_source)
        blob_from_container = blob_from_info[0]
        blob_name = blob_from_info[1]
        try:
            settings = get_storage_settings()
            toContainer = settings.uploaded_files_container
            if(blob_from_container == settings.data_source_split_files_container):
                toContainer = settings.uploaded_split_files_container
            success = await a_move_blob(blob_name,
                    blob_from_container, 
                    toContainer)
            outputMessage = f"Blob moved from {blob_from_container} to {toContainer}"
            if success == False:
                outputMessage = "Blob not found"
            valueToReturn = ValueToAzAISearch(item.recordId,
                                            DataToAzAISearch(blob_name, outputMessage),
                                            None, 
                                            None)
            return valueToReturn
        except Exception as err:
            infoErr = {"fileUrl": fileUrl, "Error": str(err)} 
            logger.exception(str(err))
            logger.track_event(event_types.move_files_exception, infoErr)  
            dataError = [{ "message": "Error: " + str(err)}]
            errorToReturn = ValueToAzAISearch(item.recordId, {}, dataError, None)
            return errorToReturn