from datetime import datetime, timedelta, timezone
import io
from functools import cache
from azure.core.credentials import AzureNamedKeyCredential
from azure.storage.blob.aio import BlobClient, BlobServiceClient
from azure.storage.blob import (
    generate_blob_sas,
    BlobSasPermissions,
)
from utils.settings import get_storage_settings


def get_azure_named_key_credential():
    settings = get_storage_settings()
    account_name = settings.account_name
    account_key = settings.account_key
    credential = AzureNamedKeyCredential(account_name, account_key)

    return credential


def generate_blob_sas_from_blob_client(blob_client: BlobClient):
    # Create a SAS token that's valid for one day, as an example
    start_time = datetime.now(timezone.utc)
    expiry_time = start_time + timedelta(days=1)
    settings = get_storage_settings()
    account_key = settings.account_key

    sas_token = generate_blob_sas(
        account_name=blob_client.account_name,
        container_name=blob_client.container_name,
        blob_name=blob_client.blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiry_time,
        start=start_time
    )

    return sas_token


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
    await blob_client.close()
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
    await blob_client.close()
    return blob_text


async def a_get_blob_stream_from_container(container: str, filename: str):
    """
    Get a blob from a container
    """
    blob_service_client = get_blob_service_client()
    blob_client = blob_service_client.get_blob_client(container,
                                                      filename)
    stream = io.BytesIO()
    downloader = await blob_client.download_blob(max_concurrency=1)
    await downloader.readinto(stream)
    return stream


def get_blob_info_container_and_blobName(url_source: str) -> tuple[str, str]:
    """
    Get the container and the name of a blob
    """
    credential = get_azure_named_key_credential()
    blob_client = BlobClient.from_blob_url(url_source, credential)
    return (blob_client.container_name, blob_client.blob_name)


async def a_get_blobName_and_metadata_for_tagging(url_source: str) -> tuple[str, dict[str, str]]:
    """
    Get the container and the metadata of a blob
    """
    credential = get_azure_named_key_credential()
    blob_client = BlobClient.from_blob_url(url_source, credential)
    blob_properties = await blob_client.get_blob_properties()
    await blob_client.close()
    return (blob_properties.name, blob_properties.metadata)


def get_blob_client_from_blob_storage_path(blob_storage_path: str):
    credential = get_azure_named_key_credential()
    blob_client = BlobClient.from_blob_url(blob_storage_path, credential)
    return blob_client


async def a_create_metadata_on_blob(url_source: str, metadataKey: str, metadataValue: str):
    """
    Add new metadata on the blob
    """
    blob_service_client = get_blob_service_client()
    (container, filename) = get_blob_info_container_and_blobName(url_source)
    blob_client = blob_service_client.get_blob_client(container,
                                                      filename)
    properties = await blob_client.get_blob_properties()
    blob_metadata = properties.metadata
    more_blob_metadata = {metadataKey: metadataValue}
    blob_metadata.update(more_blob_metadata)
    await blob_client.set_blob_metadata(metadata=blob_metadata)
    await blob_client.close()


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
        await source_blob.close()
        await dest_blob.close()
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
    await blob_client.close()
