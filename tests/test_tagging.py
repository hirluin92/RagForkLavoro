import json
import uuid
import pytest

import azure.functions as func
from metadataTagging import  metadataTagging
from logics.tagging import (a_get_all_blob_metadata, a_get_or_create_console_file_id,
                            a_get_folders_name, a_get_tags_from_blob_info, a_get_files_tags)
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

@pytest.mark.asyncio
async def test_a_get_folders_name_ok(mocker, mock_blob_client):
    # Arrange
    mocker.patch(
        "azure.storage.blob.BlobClient.from_blob_url",
         return_value=mock_blob_client
    )

    # Act
    result = await a_get_folders_name("fileUrl")

    # Assert
    assert len(result) == 1
    assert result[0] == "asilonido"

@pytest.mark.asyncio
async def test_a_get_tags_from_blob_info_ok(mocker):
    # Arrange
    mock_logger = MockLogger()
    mock_value_data = mocker.Mock()
    mock_value_data.fileUrl = "url"
    mock_value_data.fileSasToken = "token"
    mock_value = mocker.Mock()
    mock_value.recordId = "123"
    mock_value.data = mock_value_data

    mock_folders = ["naspi"]
    mock_file_id = "guid1"
    mock_metadata = ["sezione:ammortizzatori", "file_id:guid1"]
    mocker.patch("logics.tagging.a_create_metadata_on_blob",
                 return_value = None)
    mocker.patch("logics.tagging.a_get_folders_name",
                 return_value = mock_folders)
    mocker.patch("logics.tagging.a_get_or_create_console_file_id",
                 return_value = mock_file_id)
    mocker.patch("logics.tagging.a_get_all_blob_metadata",
                 return_value = mock_metadata)
    
    # Act
    results = await a_get_tags_from_blob_info(mock_value, mock_logger)
    
    # Assert
    assert results.recordId == '123'
    assert len(results.data.folders) == 1
    assert results.data.folders[0] == 'naspi'
    assert len(results.data.storageMetadata) == 2
    assert results.data.sqlDocumentId == "guid1"
    assert results.errors == None
    assert results.warnings == None

@pytest.mark.asyncio
async def test_get_tags_from_blob_info_client_error(mocker):
    # Arrange
    mock_logger = MockLogger()

    mock_value = mocker.Mock()
    mock_value.recordId = "123"
    mock_value_data = mocker.Mock()
    mock_value_data.fileUrl = "url"
    mock_value_data.fileSasToken = "token"
    mock_value.data = mock_value_data
   
    mock_error = Exception('errore')

    mocker.patch("logics.tagging.a_get_folders_name",
                     return_value = mock_error)

    # Act
    response = await a_get_tags_from_blob_info(mock_value, mock_logger)

    # Assert
    assert response.recordId == '123'
    assert response.data == {}
    assert len(response.errors) == 1
    assert 'Error: ' in response.errors[0]['message']
    assert response.warnings == None

@pytest.mark.asyncio
async def test_get_files_tags_ok(mocker):
    # Arrange
    mock_logger = MockLogger()
    mock_req_body = mocker.Mock()
    mock_value_data = mocker.Mock()
    mock_value_data.fileUrl = "url"
    mock_value_data.fileSasToken = "token"
    mock_value = mocker.Mock()
    mock_value.recordId = "123"
    mock_value.data = mock_value_data
    mock_req_body.values = [mock_value]
    mock_data_to_return = mocker.Mock()
    mock_data_to_return.folders = "asilonido"
    mock_data_to_return.storageMetadata = ['key:value']
    mock_data_to_return.storageTags = []
    get_blob_info_return_value = mocker.Mock()
    get_blob_info_return_value.recordId = "123"
    get_blob_info_return_value.data = mock_data_to_return
    get_blob_info_return_value.errors = None
    get_blob_info_return_value.warnings = None
        
    mocker.patch("logics.tagging.a_get_tags_from_blob_info",
                     return_value = get_blob_info_return_value)
    # Act
    results = await a_get_files_tags(mock_req_body, mock_logger)
    
    # Assert
    assert len(results.values) == 1
    firstValue = results.values[0]
    assert firstValue.recordId == '123'
    assert firstValue.data.folders == 'asilonido'
    assert len(firstValue.data.storageMetadata) == 1
    assert firstValue.data.storageMetadata[0] == 'key:value'
    assert len(firstValue.data.storageTags) == 0
    assert firstValue.errors == None
    assert firstValue.warnings == None

@pytest.mark.asyncio
async def test_metadataTagging_no_body(mocker):
    #Arrange
    set_mock_logger_builder(mocker)

    req = func.HttpRequest(method='POST',
                        headers={'Content-Type':'application/json'},
                        body=None,
                        url='/api/metadataTagging')
    mock_trace_context = mocker.Mock()
    
    #Act
    func_call = metadataTagging.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    
    #Assert
    assert response.status_code == 500

@pytest.mark.asyncio
async def test_metadataTagging_missing_body_values(mocker):
    #Arrange
    set_mock_logger_builder(mocker)
    req_body = {
        "avalues":[]
    }
    req = func.HttpRequest(method='POST',
                       headers={'Content-Type':'application/json'},
                       body=bytes(json.dumps(req_body), "utf-8"),
                       url='/api/metadataTagging')
    mock_trace_context = mocker.Mock()
    
    #Act
    func_call = metadataTagging.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    
    #Assert
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_metadataTagging_missing_body_recordId(mocker):
    #Arrange
    set_mock_logger_builder(mocker)
    req_body = {
        "values":[
            {
                "arecordId":"",
                "data":""
            }
        ]
    }
    req = func.HttpRequest(method='POST',
                        headers={'Content-Type':'application/json'},
                        body=bytes(json.dumps(req_body), "utf-8"),
                        url='/api/metadataTagging')
    mock_trace_context = mocker.Mock()
    
    #Act
    func_call = metadataTagging.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    
    #Assert
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_tagging_missing_body_data(mocker):
    #Arrange
    set_mock_logger_builder(mocker)
    req_body = {
        "values":[
            {
                "recordId":"",
                "adata":""
            }
        ]
    }
    req = func.HttpRequest(method='POST',
                        headers={'Content-Type':'application/json'},
                        body=bytes(json.dumps(req_body), "utf-8"),
                        url='/api/tagging')
    mock_trace_context = mocker.Mock()
    
    #Act
    func_call = metadataTagging.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    
    #Assert
    assert response.status_code == 422

