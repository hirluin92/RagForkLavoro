import json
import pytest

import azure.functions as func
from tagging import tagging
from logics.tagging import a_get_files_tags, a_get_tags_from_blob_info
from services.storage import a_get_blobName_and_metadata_for_tagging
from tests.mock_logging import MockLogger, set_mock_logger_builder

@pytest.fixture
def mock_tagging_client(mocker):
    mock_blob_client = mocker.AsyncMock()
    mock_properties = mocker.Mock()
    mock_properties.name = "asilonido/file1.txt"
    mock_properties.metadata = {
        'key':'value'
    }
    mock_blob_client.get_blob_properties.return_value = mock_properties

    return mock_blob_client

@pytest.mark.asyncio
async def test_get_blob_info_for_tagging_ok(mocker, mock_tagging_client):
    # Arrange
    mocker.patch(
        "azure.storage.blob.BlobClient.from_blob_url",
         return_value=mock_tagging_client
    )

    # Act
    result = await a_get_blobName_and_metadata_for_tagging("fileUrl")

    # Assert expected output
    assert len(result) == 2
    assert result[0] == "asilonido/file1.txt"
    assert result[1].get("key") == "value"

@pytest.mark.asyncio
async def test_get_tags_from_blob_info_ok(mocker):
    # Arrange
        mock_logger = MockLogger()

        mock_value_data = mocker.Mock()
        mock_value_data.fileUrl = "url"
        mock_value_data.fileSasToken = "token"

        mock_value = mocker.Mock()
        mock_value.recordId = "123"
        mock_value.data = mock_value_data

        mock_patch_return_value = ("asilonido/file1.txt", 
                                   {"key": "value", "id_sql_document": "id"})
        mocker.patch("logics.tagging.a_get_blob_info_for_tagging",
                     return_value = mock_patch_return_value)
    # Act
        results = await a_get_tags_from_blob_info(mock_value, mock_logger)
    # Assert
        assert results.recordId == '123'
        assert len(results.data.folders) == 1
        assert results.data.folders[0] == 'asilonido'
        assert len(results.data.storageMetadata) == 1
        assert results.data.storageMetadata[0] == 'key:value'
        assert results.data.sqlDocumentId == "id"
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
   
    get_blob_info_return_value = Exception('errore')

    mocker.patch("logics.tagging.a_get_blob_info_for_tagging",
                     return_value = get_blob_info_return_value)

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
async def test_tagging_no_body(mocker):
    #Arrange
    set_mock_logger_builder(mocker)

    req = func.HttpRequest(method='POST',
                        headers={'Content-Type':'application/json'},
                        body=None,
                        url='/api/tagging')
    mock_trace_context = mocker.Mock()
    #Act
    func_call = tagging.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    #Assert
    assert response.status_code == 500

@pytest.mark.asyncio
async def test_tagging_invalid_missing_body_values(mocker):
    #Arrange
    set_mock_logger_builder(mocker)

    req_body = {
        "avalues":[]
    }
    req = func.HttpRequest(method='POST',
                       headers={'Content-Type':'application/json'},
                       body=bytes(json.dumps(req_body), "utf-8"),
                       url='/api/tagging')
    mock_trace_context = mocker.Mock()
    #Act
    func_call = tagging.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    #Assert
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_tagging_missing_body_value_recordId(mocker):
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
                        url='/api/tagging')
    mock_trace_context = mocker.Mock()
    #Act
    func_call = tagging.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    #Assert
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_tagging_missing_body_value_data(mocker):
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
    func_call = tagging.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    #Assert
    assert response.status_code == 422
