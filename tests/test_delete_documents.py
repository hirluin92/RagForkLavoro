
import azure.functions as func
import pytest
from delete_documents import deleteDocuments
from logics.delete_documents import a_delete_by_tag
from services.search import a_delete_document_by_id, a_get_documents_by_tag
from services.storage import a_delete_blob_from_container
from tests.mock_aiohttp import MockClientResponse, MockClientSession
from tests.mock_env import set_mock_env
from tests.mock_logging import MockLogger, set_mock_logger_builder
from utils.settings import get_search_settings, get_storage_settings


@pytest.mark.asyncio
async def test_delete_blob_from_container_ok(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)
    mock_blob_client = mocker.AsyncMock()
    mock_blob_client.exists.return_value = True
    mock_blob_client.delete_blob.return_value = None
    mock_blob_service_client = mocker.Mock()
    mock_blob_service_client.get_blob_client.return_value = mock_blob_client
    mocker.patch(
        "services.storage.get_blob_service_client",
         return_value=mock_blob_service_client
    )

    # Act
    result = await a_delete_blob_from_container("container","filename")

    # Assert expected output
    mock_blob_service_client.get_blob_client.assert_called_once()
    mock_blob_client.delete_blob.assert_called_once()
    assert result

@pytest.mark.asyncio
async def test_delete_document_by_id_ok(mocker,monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)

    mock_session = mocker.AsyncMock()
    mock_session.post.return_value = None
    
    # Act
    # Assert
    await a_delete_document_by_id(mock_session,'id')

@pytest.mark.asyncio
async def test_delete_document_by_id_error(mocker,monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)

    mock_request_result = mocker.Mock()
    mock_request_result.status_code = 400
    mock_request_result.json.return_value = "Errore"
    mock_request_result.raise_for_status.side_effect = Exception("Error")
    mocker.patch("aiohttp.ClientSession.post",
                     return_value = mock_request_result)
    
    # Act
    # Assert
    with pytest.raises(Exception):
        await a_delete_document_by_id('id')

@pytest.mark.asyncio
async def test_get_documents_by_tag_ok(mocker,monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)

    
    mock_result_data = {
        "value": [
            {"chunk_id": "id",
             "filename":"name",
             "blob_name":"nameb",
             "tags":["tag1"]}],
        "@odata.nextLink": "link"
    }
    mock_response = MockClientResponse(mock_result_data,200)
    mock_session = MockClientSession(mock_response)
    
    # Act
    result = await a_get_documents_by_tag(mock_session,'tag')
    # Assert
    assert result.nextPage == True
    assert len(result.value) == 1
    assert result.value[0].chunk_id == "id"
    assert result.value[0].filename == "name"
    assert result.value[0].blob_name == "nameb"
    assert result.value[0].tags[0] == "tag1"

@pytest.mark.asyncio
async def test_get_documents_by_tag_error(mocker,monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)

    mocker.patch("aiohttp.ClientSession.get",
                     side_effect = Exception)
    
    # Act
    # Assert
    with pytest.raises(Exception):
        await a_get_documents_by_tag('tag')

@pytest.mark.asyncio
async def test_delete_by_tag_ok(mocker,monkeypatch):
    # Arrange
    mock_logger = MockLogger()
    mock_session = mocker.Mock()

    set_mock_env(monkeypatch)

    mock_documents = mocker.Mock()
    mock_documents.value = [mocker.Mock(blob_name="name",chunk_id="id")]
    mock_documents.nextPage = False
    mocker.patch("logics.delete_documents.a_get_documents_by_tag",
                     return_value = mock_documents)
    
    mocker.patch("logics.delete_documents.a_delete_document_by_id",
                     return_value = None)
    
    mocker.patch("logics.delete_documents.a_delete_blob_from_container",
                     return_value = None)
    
    # Act
    await a_delete_by_tag('tag',mock_logger,mock_session)

    # Assert

@pytest.mark.asyncio
async def test_delete_by_tag_ko(mocker,monkeypatch):
    # Arrange
    mock_logger = MockLogger()

    set_mock_env(monkeypatch)

    mock_documents = mocker.Mock()
    mock_documents.value = [mocker.Mock(blob_name="name",chunk_id="id")]
    mock_documents.nextPage = False
    mocker.patch("logics.delete_documents.a_get_documents_by_tag",
                     return_value = mock_documents)
    
    mocker.patch("logics.delete_documents.a_delete_document_by_id",
                     side_effect = Exception("Error"))
    
    mocker.patch("logics.delete_documents.a_delete_blob_from_container",
                     return_value = None)
    
    # Act
    # Assert
    with pytest.raises(Exception):
        await a_delete_by_tag('tag', mock_logger)

@pytest.mark.asyncio
async def test_deleteDocuments_missing_environment_variables(mocker):
    #Arrange
    get_search_settings.cache_clear()
    get_storage_settings.cache_clear()
    set_mock_logger_builder(mocker)
    
    req = func.HttpRequest(method='DELETE',
                        url='/api/deleteDocumentsByTag',
                        body=None,
                        route_params={"tag": "tag"})
    
    mock_trace_context = mocker.Mock()
    #Act
    func_call = deleteDocuments.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    #Assert
    assert response.status_code == 500

@pytest.mark.asyncio
async def test_deleteDocuments_ko(mocker, monkeypatch):
    #Arrange
    set_mock_logger_builder(mocker)

    set_mock_env(monkeypatch)

    mocker.patch("delete_documents.a_delete_by_tag",
                     side_effect = Exception("Errore"))
    
    req = func.HttpRequest(method='DELETE',
                        url='/api/deleteDocumentsByTag',
                        body=None,
                        route_params={"tag": "tag"})
    
    mock_trace_context = mocker.Mock()
    #Act
    #Assert
    func_call = deleteDocuments.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    #Assert
    assert response.status_code == 500

@pytest.mark.asyncio
async def test_deleteDocuments_ok(mocker, monkeypatch):
    #Arrange
    set_mock_logger_builder(mocker)

    set_mock_env(monkeypatch)

    mocker.patch("delete_documents.a_delete_by_tag",
                     return_value = None)
    
    req = func.HttpRequest(method='DELETE',
                        url='/api/deleteDocumentsByTag',
                        body=None,
                        route_params={"tag": "tag"})
    
    mock_trace_context = mocker.Mock()
    #Act
    func_call = deleteDocuments.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    #Assert
    assert response.status_code == 204