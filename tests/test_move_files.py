import json
from pydantic import ValidationError

import azure.functions as func
import pytest
from move_files import move_files
from logics.move_files import a_move_all_data_response, a_move_item
from services.storage import *
from tests.mock_env import set_mock_env
from tests.mock_logging import set_mock_logger_builder


def test_get_blob_info_for_move_ok(monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)
    fileUrl = "https://genaipltstdev.blob.core.windows.net/movefiles-end/asilo/my_documento_assegno_unico.pdf"
    fileSasToken = "?sasToken"
    source = fileUrl + fileSasToken

    # Act
    result = get_blob_info_container_and_blobName(source)

    # Assert expected output
    assert len(result) == 2
    assert result[0] == "movefiles-end"
    assert result[1] == "asilo/my_documento_assegno_unico.pdf"

@pytest.mark.asyncio
async def test_move_blob_ok(mocker):
    # Arrange
    blobPath = "sfl/title.txt"
    fromContainer = "start"
    toContainer = "end"
    
    mock_client = mocker.AsyncMock()
    mock_client.exists.return_value = True
    mock_service_client = mocker.Mock()
    mock_service_client.get_blob_client.return_value = mock_client
    mocker.patch(
        "services.storage.get_blob_service_client",
        return_value = mock_service_client
    ) 
    mocker.patch("azure.storage.blob.BlobClient.start_copy_from_url")
    mocker.patch("azure.storage.blob.BlobClient.delete_blob")

    # Act
    await a_move_blob(blobPath, fromContainer, toContainer)

@pytest.mark.asyncio
async def test_move_item_ok(mocker):
    # Arrange
    set_mock_logger_builder(mocker)
    mock_trace_context = mocker.Mock()

    mock_value_data = mocker.Mock()
    mock_value_data.fileUrl = "https://genaipltstdev.blob.core.windows.net/movefiles-end/asilo/my_documento_assegno_unico.pdf"
    mock_value_data.fileSasToken = "token"
    mock_value = mocker.Mock()
    mock_value.recordId = "123"
    mock_value.data = mock_value_data
    mock_patch_return_value = ('movefiles-end','asilo/my_documento_assegno_unico.pdf')
    mocker.patch("logics.move_files.get_storage_settings")
    mocker.patch("logics.move_files.get_blob_info_container_and_blobName",
                  return_value = mock_patch_return_value)
    mocker.patch("logics.move_files.a_move_blob")
        
    # Act
    result = await a_move_item(mock_value, mock_trace_context)

    # Assert
    assert result.recordId == '123'
    assert result.data.blobName == 'asilo/my_documento_assegno_unico.pdf'
    assert result.errors == None
    assert result.warnings == None

@pytest.mark.asyncio
async def test_move_item_client_error(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)
    set_mock_logger_builder(mocker)
    mock_trace_context = mocker.Mock()

    mock_value_data = mocker.Mock()
    mock_value_data.fileUrl = "https://genaipltstdev.blob.core.windows.net/movefiles-end/asilo/my_documento_assegno_unico.pdf"
    mock_value_data.fileSasToken = "token"
    mock_value = mocker.Mock()
    mock_value.recordId = "123"
    mock_value.data = mock_value_data

    exception = Exception('error')
    mocker.patch("logics.move_files.get_storage_settings")
    mocker.patch("logics.move_files.a_move_blob",
                     side_effect = exception)

    # Act
    result = await a_move_item(mock_value, mock_trace_context)

    # Assert
    assert result.recordId == '123'
    assert result.data == {}
    assert len(result.errors) == 1
    assert 'Error: ' in result.errors[0]['message']
    assert result.warnings == None

@pytest.mark.asyncio
async def test_move_all_data_response_ok(mocker):
    # Arrange
    set_mock_logger_builder(mocker)
    mock_trace_context = mocker.Mock()

    mock_req_body = mocker.Mock()
    mock_value_data = mocker.Mock()
    mock_value_data.fileUrl = "url"
    mock_value_data.fileSasToken = "token"
    mock_value = mocker.Mock()
    mock_value.recordId = "123"
    mock_value.data = mock_value_data
    mock_req_body.values = [mock_value]

    mock_data_to_return = mocker.Mock()
    mock_data_to_return.blobName = "auu/file1.txt"
    move_item_return_value = mocker.Mock()
    move_item_return_value.recordId = "123"
    move_item_return_value.data = mock_data_to_return
    move_item_return_value.errors = None
    move_item_return_value.warnings = None

    mocker.patch("logics.move_files.get_storage_settings")
    mocker.patch("logics.move_files.a_move_item",
                return_value = move_item_return_value)

    # Act
    results = await a_move_all_data_response(mock_req_body, mock_trace_context)

    # Assert
    assert len(results.values) == 1
    firstValue = results.values[0]
    assert firstValue.recordId == '123'
    assert firstValue.data.blobName == 'auu/file1.txt'
    assert firstValue.errors == None
    assert firstValue.warnings == None

@pytest.mark.asyncio
async def test_moveFiles_no_body(mocker):
    #Arrange
    set_mock_logger_builder(mocker)
    mock_trace_context = mocker.Mock()

    req = func.HttpRequest(method='POST',
                        headers={'Content-Type':'application/json'},
                        body=None,
                        url='/api/moveFiles')
    
    #Act
    func_call = move_files.build().get_user_function()
    response = await func_call(req, mock_trace_context)

    #Assert
    assert response.status_code == 500

@pytest.mark.asyncio
async def test_moveFiles_missing_body_value(mocker):
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
                       url='/api/moveFiles')
    
    mocker.patch("move_files.get_storage_settings")

    #Act
    func_call = move_files.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    
    #Assert
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_moveFiles_settings_exception(mocker):
    # Arrange
    set_mock_logger_builder(mocker)
    mock_trace_context = mocker.Mock()

    mock_storage_setting_exception = ValidationError
    mocker.patch("move_files.get_storage_settings",
                 return_value = mock_storage_setting_exception)
    
    req = func.HttpRequest(method='POST',
                        headers={'Content-Type':'application/json'},
                        body=None,
                        url='/api/moveFiles')
    
    #Act
    func_call = move_files.build().get_user_function()
    response = await func_call(req, mock_trace_context)

    #Assert
    assert response.status_code == 500
    



