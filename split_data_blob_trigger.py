import azure.functions as func
import os
from logics.split_data import a_split_data_into_chunks
from services.logging import LoggerBuilder
import constants.event_types as event_types

bp = func.Blueprint()


@bp.function_name("splitData")
@bp.blob_trigger(arg_name="myblob", path=os.getenv("STORAGE_BULK_SPLIT_FILES_CONTAINER"), connection="STORAGE_CONNECTION_STRING") 
async def split_data(myblob: func.InputStream, context: func.Context):
    with LoggerBuilder(__name__, context) as logger:
        logger.info(f"Python blob trigger function processed blob: {myblob.name}")
        propertiesDict = {"Title": myblob.name.split('/')[-1],
                        "BlobUri": myblob.uri, 
                        "SourceContainer":myblob.name.split('/')[0]}
        try:
            (chunks, dest_container) = await a_split_data_into_chunks(myblob) 
            propertiesDict.update({"NumberOfChunks": chunks, "DestinationContainer":dest_container})
            logger.track_event(event_types.split_data_result, propertiesDict)  
        except Exception as err:
            logger.exception(str(err))
            logger.track_event(event_types.split_data_exception, propertiesDict)  
    