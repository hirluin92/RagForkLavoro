
from aiohttp import ClientSession
from constants import event_types
from services.logging import Logger
from services.search import a_delete_document_by_id, a_get_documents_by_tag
from services.storage import a_delete_blob_from_container
from utils.settings import get_storage_settings


async def a_delete_by_tag(tag: str,logger: Logger,session:ClientSession):
    storage_settings = get_storage_settings()
    exist_documents = True
    deleted_documents = 0
    while exist_documents:
        documents = await a_get_documents_by_tag(session,
                                                 tag)
        if len(documents.value) > 0:
            for document in documents.value:
                filename = document.blob_name
                try:
                    await a_delete_document_by_id(session,
                                                  document.chunk_id)
                    deleted = await a_delete_blob_from_container(
                        storage_settings.uploaded_files_container, filename)
                    if not deleted:
                        await a_delete_blob_from_container(
                        storage_settings.uploaded_split_files_container, filename)
                except Exception as error:
                    error_message = "File-Document processing error. File: {file} | Document: {document} | Error: {error}"
                    logger.exception(error_message.format(file=document.blob_name,
                                                          document=document.chunk_id,
                                                          error=str(error)))
                    raise error
        exist_documents = documents.nextPage
        if deleted_documents == 0:
            deleted_documents=documents.count


    logger.track_event(event_types.documents_deleted_event, 
                               { 
                                "documents_deleted": deleted_documents, 
                                "tag": tag
                                })