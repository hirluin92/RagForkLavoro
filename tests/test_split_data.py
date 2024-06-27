import pytest

import azure.functions as func
from split_data_blob_trigger import split_data
from logics.split_data import a_split_data_into_chunks
from tests.mock_logging import set_mock_logger_builder
from services.storage import get_blob_service_client, a_upload_txt_to_blob, a_delete_blob_from_container
from tests.mock_logging import set_mock_logger_builder 


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
async def test_split_data_into_chunks_ok(mocker):
    # Arrange
    mock_inputStream = mocker.Mock()
    mock_inputStream.name = "origin_container/sfl/title.txt"
    mock_bytes = mocker.Mock()
    mock_inputStream.read.return_value = mock_bytes 
    mock_bytes.decode.return_value = "chunk1\r\n\r\n\r\nchunk2\r\n\r\n\r\nchunk3"
        
    mock_setting = mocker.Mock()
    mock_setting.data_source1 = "source"
    mocker.patch("logics.split_data.get_storage_settings",
                 return_value = mock_setting)
    mocker.patch("logics.split_data.a_upload_txt_to_blob")
    mocker.patch("logics.split_data.a_delete_blob_from_container")

    # Act
    results = await a_split_data_into_chunks(mock_inputStream)

    # Assert
    assert results[0] == 3

@pytest.mark.asyncio
async def test_split_data_into_chunks_client_error(mocker):
    # Arrange
    mock_inputStream = mocker.Mock()
    mock_inputStream.name = "origin_container/sfl/title.txt"
    mock_bytes = mocker.Mock()
    mock_inputStream.read.return_value = mock_bytes 
    mock_bytes.decode.return_value = "chunk1\r\n\r\n\r\nchunk2\r\n\r\n\r\nchunk3"
        
    mock_setting = mocker.Mock()
    mock_setting.data_source1 = "source"
    mocker.patch("logics.split_data.get_storage_settings",
                 return_value = mock_setting)
    error_return_value = Exception('errore')
    mocker.patch("logics.split_data.a_upload_txt_to_blob",
                 side_effect = error_return_value)

    # Act
    with pytest.raises(Exception):
        await a_split_data_into_chunks(mock_inputStream)

@pytest.mark.asyncio
async def test_splitData_blob_trigger_ok(mocker):
    # Arrange
    set_mock_logger_builder(mocker)
    mock_trace_context = mocker.Mock()

    blob_data = "chunk1\r\n\r\n\r\nchunk2\r\n\r\n\r\nchunk3"
    blob_name = "source_container/sfl/file1.txt"
    blob_uri = "www.blobUri.it"
    req = func.blob.InputStream(data=blob_data.encode("utf8"), 
                                name = blob_name,
                                uri= blob_uri)
    mock_split_data_value = (3, 'target container')
    mocker.patch("split_data_blob_trigger.a_split_data_into_chunks",
                 return_value = mock_split_data_value)
    
    # Act
    func_call = split_data.build().get_user_function()
    await func_call(req, mock_trace_context)

@pytest.mark.asyncio
async def test_splitData_blob_trigger_error(mocker):
    # Arrange
    set_mock_logger_builder(mocker)
    mock_trace_context = mocker.Mock()

    blob_data = "chunk1\r\n\r\n\r\nchunk2\r\n\r\n\r\nchunk3"
    blob_name = "source_container/sfl/file1.txt"
    blob_uri = "www.blobUri.it"
    req = func.blob.InputStream(data=blob_data.encode("utf8"), 
                                name = blob_name,
                                uri= blob_uri)

    mock_split_data_error = Exception('errore')
    mocker.patch("split_data_blob_trigger.a_split_data_into_chunks",
                 return_value = mock_split_data_error)
    
    #Act
    func_call = split_data.build().get_user_function()
    await func_call(req, mock_trace_context)



    
    