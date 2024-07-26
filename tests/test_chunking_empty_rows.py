import json
from pydantic import ValidationError
import pytest

import azure.functions as func
from tests.mock_logging import MockLogger, set_mock_logger_builder
from services.storage import get_blob_service_client, a_upload_txt_to_blob, a_delete_blob_from_container
from tests.mock_logging import set_mock_logger_builder 
from logics.split_data import a_split_text_into_chunks, a_custom_chunking
from chunking_empty_rows import chunkingEmptyRows


def test_get_blob_service_client_ok(mocker):
    # Arrange
    mock_service_client = mocker.Mock()
    mocker.patch("services.storage.get_storage_settings")
    mocker.patch(
        "azure.storage.blob.BlobServiceClient.from_connection_string",
        return_value=mock_service_client
    )

    # Act
    result = get_blob_service_client()

@pytest.mark.asyncio
async def test_upload_blob_txt_ok(mocker):
    # Arrange
    blobPath = "sfl/title.txt"
    container = "container"
    text = "content txt"
    mock_client = mocker.AsyncMock()
    mock_client.upload_blob.return_value = {"data":"value"}
    mock_service_client = mocker.Mock()
    mock_service_client.get_blob_client.return_value = mock_client
    mocker.patch(
        "services.storage.get_blob_service_client",
        return_value = mock_service_client
    ) 

    # Act
    await a_upload_txt_to_blob(container, blobPath, text)

    # Assert
    mock_client.upload_blob.assert_called_once()

@pytest.mark.asyncio
async def test_delete_blob_from_container_ok(mocker):
    # Arrange
    blobPath = "sfl/title.txt"
    container = "container"
    mock_client = mocker.AsyncMock()
    mock_client.exists.return_value = True
    mock_client.delete_blob.return_value = None
    mock_service_client = mocker.Mock()
    mock_service_client.get_blob_client.return_value = mock_client
    mocker.patch(
        "services.storage.get_blob_service_client",
        return_value = mock_service_client
    ) 

    # Act
    await a_delete_blob_from_container(container, blobPath)

    # Assert
    mock_client.delete_blob.assert_called_once()

@pytest.mark.asyncio
async def test_a_split_text_into_chunks_ok(mocker):
    # Arrange
    mock_logger = MockLogger()
    mock_value_data = mocker.Mock()
    mock_value_data.fileUrl = "https://genaipltstdev.blob.core.windows.net/data1/auu/assegno_unico_prova.txt"
    mock_value_data.fileSasToken = "?token"

    mock_value = mocker.Mock()
    mock_value.recordId = "123"
    mock_value.data = mock_value_data

    mocker.patch("logics.split_data.get_blob_info_container_and_blobName",
                 return_value = ("container", "name"))

    mock_text_content = "chunk1\r\n\r\n\r\nchunk2\r\n\r\n\r\nchunk3"
    mocker.patch("logics.split_data.a_get_blob_content_from_container",
                 return_value = mock_text_content)

    # Act
    results = await a_split_text_into_chunks(mock_value, mock_logger)

    # Assert
    assert results.recordId == '123'
    assert len(results.data.chunksList) == 3
    assert results.errors == None
    assert results.warnings == None

@pytest.mark.asyncio
async def test_a_split_text_into_chunks_client_error(mocker):
    # Arrange
    mock_logger = MockLogger()
    mock_value_data = mocker.Mock()
    mock_value_data.fileUrl = "https://genaipltstdev.blob.core.windows.net/data1/auu/assegno_unico_prova.txt"
    mock_value_data.fileSasToken = "?token"

    mock_value = mocker.Mock()
    mock_value.recordId = "123"
    mock_value.data = mock_value_data

    mock_text_content_error = Exception('errore')
    mocker.patch("logics.split_data.a_get_blob_content_from_container",
                 return_value = mock_text_content_error)

    # Act
    response = await a_split_text_into_chunks(mock_value, mock_logger)

    # Assert
    assert response.recordId == '123'
    assert response.data == {}
    assert len(response.errors) == 1
    assert 'Error: ' in response.errors[0]['message']
    assert response.warnings == None

@pytest.mark.asyncio
async def test_a_custom_chunking_ok(mocker):
    # Arrange
        mock_logger = MockLogger()
        mock_req_body = mocker.Mock()

        mock_value_data = mocker.Mock()
        mock_value_data.fileUrl = "https://genaipltstdev.blob.core.windows.net/data1/auu/assegno_unico_prova.txt"
        mock_value_data.fileSasToken = "?token"
        mock_value = mocker.Mock()
        mock_value.recordId = "123"
        mock_value.data = mock_value_data
        mock_req_body.values = [mock_value]

        mock_data_to_return = mocker.Mock()
        mock_data_to_return.chunksList = ["chunk1", "chunk2"]
        mock_splitted_chunks = mocker.Mock()
        mock_splitted_chunks.recordId = "123"
        mock_splitted_chunks.data = mock_data_to_return
        mock_splitted_chunks.errors = None
        mock_splitted_chunks.warnings = None
        
        mocker.patch("logics.split_data.a_split_text_into_chunks",
                     return_value = mock_splitted_chunks)
    # Act
        results = await a_custom_chunking(mock_req_body, mock_logger)
    # Assert
        assert len(results.values) == 1
        firstValue = results.values[0]
        assert firstValue.recordId == '123'
        assert len(firstValue.data.chunksList) == 2
        assert firstValue.errors == None
        assert firstValue.warnings == None

@pytest.mark.asyncio
async def test_chunkingEmptyRows_no_body(mocker):
    #Arrange
    set_mock_logger_builder(mocker)
    mock_trace_context = mocker.Mock()

    req = func.HttpRequest(method='POST',
                        headers={'Content-Type':'application/json'},
                        body=None,
                        url='/api/chunkingEmptyRows')
    
    #Act
    func_call = chunkingEmptyRows.build().get_user_function()
    response = await func_call(req, mock_trace_context)

    #Assert
    assert response.status_code == 500

@pytest.mark.asyncio
async def test_chunkingEmptyRows_missing_body_value(mocker):
    #Arrange
    set_mock_logger_builder(mocker)
    mock_trace_context = mocker.Mock()

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
                       url='/api/chunkingEmptyRows')
    
    mocker.patch("chunking_empty_rows.a_custom_chunking")

    #Act
    func_call = chunkingEmptyRows.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    
    #Assert
    assert response.status_code == 422

    