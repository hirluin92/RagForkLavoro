import json
import uuid
import pytest

import azure.functions as func
from metadataTagging import  metadataTagging
from logics.tagging import a_get_all_blob_metadata, a_get_or_create_console_file_id
from services.storage import a_get_blobName_and_metadata_for_tagging, a_create_metadata_on_blob
from tests.mock_logging import MockLogger, set_mock_logger_builder

@pytest.fixture
def mock_blob_client(mocker):
    mock_blob_client = mocker.AsyncMock()
    mock_properties = mocker.Mock()
    mock_properties.name = "asilonido/file1.txt"
    mock_properties.metadata = {
        'key':'value'
    }
    mock_blob_client.get_blob_properties.return_value = mock_properties

    return mock_blob_client

@pytest.mark.asyncio
async def test_a_get_blobName_and_metadata_for_tagging_ok(mocker, mock_blob_client):
    # Arrange
    mocker.patch(
        "azure.storage.blob.BlobClient.from_blob_url",
         return_value=mock_blob_client
    )

    # Act
    result = await a_get_blobName_and_metadata_for_tagging("fileUrl")

    # Assert expected output
    assert len(result) == 2
    assert result[0] == "asilonido/file1.txt"
    assert result[1].get("key") == "value"

@pytest.mark.asyncio
async def test_a_create_metadata_on_blob_ok(mocker, mock_blob_client):
    # Arrange
    mock_url_source = "https://genaipltstdev.blob.core.windows.net/data1/auu/assegno_unico_prova.txt?token"
    mock_metadataKey = "sezione"
    mock_metadataValue = "riscatti"
    mock_metadata_properties = {
        "key1":"value1",
        "sezione":"riscatti"
    }
    mock_service_client = mocker.Mock()
    mocker.patch(
        "services.storage.get_blob_service_client",
        return_value = mock_service_client
    ) 
    mock_service_client.get_blob_client.return_value = mock_blob_client
    mock_blob_client.set_blob_metadata.return_value = mock_metadata_properties

    # Act
    result = await a_create_metadata_on_blob(mock_url_source, mock_metadataKey, mock_metadataValue)

@pytest.mark.asyncio
async def test_a_get_all_blob_metadata_ok(mocker, mock_blob_client):
    # Arrange
    mocker.patch(
        "azure.storage.blob.BlobClient.from_blob_url",
         return_value=mock_blob_client
    )

    # Act
    result = await a_get_all_blob_metadata("fileUrl")

    # Assert expected output
    assert len(result) == 1

@pytest.mark.asyncio
async def test_a_get_or_create_console_file_id_with_fileID_retrieved(mocker):
    # Arrange
    mock_blobName = "blob"
    mock_metadata = {
        "key1":"value1",
        "id_sql_document":"guid_file"
    }
    mock_blob_info_return = (mock_blobName, mock_metadata)
    mocker.patch(
        "logics.tagging.a_get_blobName_and_metadata_for_tagging",
         return_value= mock_blob_info_return
    )

    # Act
    result = await a_get_or_create_console_file_id("fileUrl")

    # Assert 
    assert result == "guid_file"

@pytest.mark.asyncio
async def test_a_get_or_create_console_file_id_with_fileID_created(mocker):
    # Arrange
    mock_blobName = "blob"
    mock_metadata = {
        "key1":"value1"
    }
    mock_blob_info_return = (mock_blobName, mock_metadata)
    mocker.patch(
        "logics.tagging.a_get_blobName_and_metadata_for_tagging",
         return_value= mock_blob_info_return
    )
    mocker.patch(
        "logics.tagging.a_create_metadata_on_blob"
    )

    # Act
    result = await a_get_or_create_console_file_id("fileUrl")

    # Assert 
    assert result is not None
    assert result != ""
    assert uuid.UUID(result)


