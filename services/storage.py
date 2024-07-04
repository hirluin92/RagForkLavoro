from datetime import *
from functools import cache
from azure.storage.blob.aio import BlobClient, BlobServiceClient
from utils.settings import get_storage_settings


@cache
def get_blob_service_client():
    """
    Get the BlobServiceClient object
    """
    settings = get_storage_settings()
    connection_string = settings.connection_string
    blob_service_client = BlobServiceClient.from_connection_string(
        connection_string)
    return blob_service_client

async def a_delete_blob_from_container(container: str, filename: str):
    """
    Delete a blob from a container
    """
    blob_service_client = get_blob_service_client()
    blob_client = blob_service_client.get_blob_client(container,
                                                      filename)
    if await blob_client.exists():
        await blob_client.delete_blob(delete_snapshots="include")
        return True
    
    return False

async def a_get_blob_content_from_container(container: str, filename: str):
    """
    Get a blob from a container
    """
    blob_service_client = get_blob_service_client()
    blob_client = blob_service_client.get_blob_client(container,
                                                      filename)
    downloader = await blob_client.download_blob(max_concurrency=1, encoding='UTF-8')
    blob_text = await downloader.readall()

    return blob_text

def get_blob_info_container_and_blobName(url_source: str) -> tuple[str, str]:
    """
    Get the container and the name of a blob
    """
    blob_client = BlobClient.from_blob_url(url_source)
    return (blob_client.container_name, blob_client.blob_name)

async def a_get_blob_info_for_tagging(url_source: str) -> tuple[str, dict[str, str]]:
    """
    Get the container and the metadata of a blob
    """
    blob_client = BlobClient.from_blob_url(url_source)
    blob_properties = await blob_client.get_blob_properties()
    return (blob_properties.name, blob_properties.metadata)

async def a_move_blob(blobNamePath: str, from_container: str, to_container: str):
    """
    Move a blob from a container to another
    """
    blob_service_client = get_blob_service_client()
    source_blob = blob_service_client.get_blob_client(
        from_container, blobNamePath)
    if await source_blob.exists():
        dest_blob = blob_service_client.get_blob_client(to_container, blobNamePath)
        await dest_blob.start_copy_from_url(source_blob.url)
        await source_blob.delete_blob(delete_snapshots="include")
        return True
    
    return False

async def a_upload_txt_to_blob(container: str, blob_name_path: str, text: str):
    """
    Upload a text to a blob
    """
    blob_service_client = get_blob_service_client()
    blob_client = blob_service_client.get_blob_client(
        container, blob_name_path)
    await blob_client.upload_blob(data=text)