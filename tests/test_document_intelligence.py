import json
import pytest

import azure.functions as func
from document_intelligence import document_intelligence
from logics.document_intelligence import a_get_documents_content, a_get_content_from_document_intelligence
from services.document_intelligence import a_analyze_layout
from tests.mock_logging import MockLogger, set_mock_logger_builder
from utils.settings import get_document_intelligence_settings

@pytest.fixture
def mock_document_intelligence_client(mocker):
    mock_client = mocker.AsyncMock()
    mock_poller = mocker.AsyncMock()
    mock_result = mocker.Mock()
    mock_result.content = "Mocked Content"
    mock_result.paragraphs = [mocker.Mock(role="header", content="Mocked Paragraph")]
    mock_result.tables = [
        mocker.Mock(
            row_count=2,
            column_count=3,
            cells=[
                mocker.Mock(content="Cell 1", row_index=0, column_index=0, kind="data"),
                mocker.Mock(content="Cell 2", row_index=0, column_index=1, kind="data"),
            ],
        )
    ]
    mock_poller.result.return_value = mock_result
    mock_client.begin_analyze_document.return_value = mock_poller
    return mock_client

@pytest.mark.asyncio
async def test_analyze_layout_ok(mocker, monkeypatch, mock_document_intelligence_client):
    # Arrange
    monkeypatch.setenv('DOCUMENT_INTELLIGENCE_KEY', 'key')
    monkeypatch.setenv('DOCUMENT_INTELLIGENCE_ENDPOINT', 'endpoint')
    mocker.patch(
        "services.document_intelligence.get_document_intelligence_client",
         return_value=mock_document_intelligence_client
    )
    # Act
    result = await a_analyze_layout("url", "outputFormat")
    # Assert expected output
    assert result[0] == "Mocked Content"
    assert len(result[1]) == 1
    assert len(result[2]) == 1

@pytest.mark.asyncio
async def test_get_content_from_document_intelligence_ok(mocker):
    # Arrange
    mock_logger = MockLogger()

    mock_value = mocker.Mock()
    mock_value.recordId = "123"
    mock_value_data = mocker.Mock()
    mock_value_data.fileUrl = "url"
    mock_value_data.fileSasToken = "token"
    mock_value.data = mock_value_data
    outputFormat = 'markdown'
   
    analyze_layout_return_value = ('content', [], [])

    mocker.patch("logics.document_intelligence.a_analyze_layout",
                     return_value = analyze_layout_return_value)

    # Act
    result = await a_get_content_from_document_intelligence(mock_value, outputFormat, mock_logger)

    # Assert
    assert result.recordId == '123'
    assert result.data.content == 'content'
    assert len(result.data.paragraphs) == 0
    assert len(result.data.tables) == 0
    assert result.errors == None
    assert result.warnings == None

@pytest.mark.asyncio
async def test_get_content_from_document_intelligence_client_error(mocker):
    # Arrange
    mock_logger = MockLogger()

    mock_value = mocker.Mock()
    mock_value.recordId = "123"
    mock_value_data = mocker.Mock()
    mock_value_data.fileUrl = "url"
    mock_value_data.fileSasToken = "token"
    mock_value.data = mock_value_data
    outputFormat = 'markdown'
   
    analyze_layout_return_value = Exception('errore')

    mocker.patch("logics.document_intelligence.a_analyze_layout",
                     return_value = analyze_layout_return_value)

    # Act
    response = await a_get_content_from_document_intelligence(mock_value, outputFormat, mock_logger)

    # Assert
    assert response.recordId == '123'
    assert response.data == {}
    assert len(response.errors) == 1
    assert 'Error: ' in response.errors[0]['message']
    assert response.warnings == None

@pytest.mark.asyncio
async def test_get_documents_content_ok(mocker, monkeypatch):
    # Arrange
    mock_logger = MockLogger()

    monkeypatch.setenv('DOCUMENT_INTELLIGENCE_KEY', 'key')
    monkeypatch.setenv('DOCUMENT_INTELLIGENCE_ENDPOINT', 'endpoint')

    outputFormat = "markdown"
        
    mock_req_body = mocker.Mock()

    mock_value_data = mocker.Mock()
    mock_value_data.fileUrl = "url"
    mock_value_data.fileSasToken = "token"

    mock_value = mocker.Mock()
    mock_value.recordId = "123"
    mock_value.data = mock_value_data

    mock_req_body.values = [mock_value]

    mock_data_to_return = mocker.Mock()
    mock_data_to_return.content = "content"
    mock_data_to_return.paragraphs = []
    mock_data_to_return.tables = []
    mock_get_content_from_doc_int = mocker.Mock()
    mock_get_content_from_doc_int.recordId = "123"
    mock_get_content_from_doc_int.data = mock_data_to_return
    mock_get_content_from_doc_int.errors = None
    mock_get_content_from_doc_int.warnings = None
        
    mocker.patch("logics.document_intelligence.a_get_content_from_document_intelligence",
                    return_value = mock_get_content_from_doc_int)
    # Act
    results = await a_get_documents_content(mock_req_body, outputFormat, mock_logger)
    # Assert
    assert len(results.values) == 1
    firstValue = results.values[0]
    assert firstValue.recordId == '123'
    assert firstValue.data.content == 'content'
    assert firstValue.errors == None
    assert firstValue.warnings == None

@pytest.mark.asyncio
async def test_documentIntelligence_no_body(mocker,
                                      monkeypatch):
    #Arrange
    set_mock_logger_builder(mocker)
    monkeypatch.setenv('DOCUMENT_INTELLIGENCE_KEY', 'key')
    monkeypatch.setenv('DOCUMENT_INTELLIGENCE_ENDPOINT', 'endpoint')
    req = func.HttpRequest(method='POST',
                        headers={'Content-Type':'application/json'},
                        body=None,
                        url='/api/documentIntelligence',
                        params={'outputFormat': 'markdown'})
    mock_trace_context = mocker.Mock()
    #Act
    func_call = document_intelligence.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    #Assert
    assert response.status_code == 500

@pytest.mark.asyncio
async def test_documentIntelligence_missing_body_values(mocker,
                                                  monkeypatch):
    #Arrange
    set_mock_logger_builder(mocker)
    monkeypatch.setenv('DOCUMENT_INTELLIGENCE_KEY', 'key')
    monkeypatch.setenv('DOCUMENT_INTELLIGENCE_ENDPOINT', 'endpoint')
    req_body = {
        "avalues":[]
    }
    req = func.HttpRequest(method='POST',
                       headers={'Content-Type':'application/json'},
                       body=bytes(json.dumps(req_body), "utf-8"),
                       url='/api/documentIntelligence',
                       params={'outputFormat': 'markdown'})
    mock_trace_context = mocker.Mock()
    #Act
    func_call = document_intelligence.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    #Assert
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_documentIntelligence_missing_body_value_recordId(mocker,
                                                          monkeypatch):
    #Arrange
    set_mock_logger_builder(mocker)
    monkeypatch.setenv('DOCUMENT_INTELLIGENCE_KEY', 'key')
    monkeypatch.setenv('DOCUMENT_INTELLIGENCE_ENDPOINT', 'endpoint')
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
                        url='/api/documentIntelligence',
                        params={'outputFormat': 'markdown'})
    mock_trace_context = mocker.Mock()
    #Act
    func_call = document_intelligence.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    #Assert
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_documentIntelligence_missing_body_value_data(mocker,
                                                      monkeypatch):
    #Arrange
    set_mock_logger_builder(mocker)
    monkeypatch.setenv('DOCUMENT_INTELLIGENCE_KEY', 'key')
    monkeypatch.setenv('DOCUMENT_INTELLIGENCE_ENDPOINT', 'endpoint')
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
                        url='/api/documentIntelligence',
                        params={'outputFormat': 'markdown'})
    mock_trace_context = mocker.Mock()
    #Act
    func_call = document_intelligence.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    #Assert
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_documentIntelligence_missing_environment_key_variable(mocker,
                                                               monkeypatch):
    #Arrange
    get_document_intelligence_settings.cache_clear()
    set_mock_logger_builder(mocker)
    monkeypatch.setenv('DOCUMENT_INTELLIGENCE_ENDPOINT', 'endpoint')
    req_body = {
        "values":[
            {
                "recordId":"",
                "data":""
            }
        ]
    }
    req = func.HttpRequest(method='POST',
                        headers={'Content-Type':'application/json'},
                        body=bytes(json.dumps(req_body), "utf-8"),
                        url='/api/documentIntelligence',
                        params={'outputFormat': 'markdown'})
    mock_trace_context = mocker.Mock()
    #Act
    func_call = document_intelligence.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    #Assert
    assert response.status_code == 500

@pytest.mark.asyncio
async def test_documentIntelligence_missing_environment_endpoint_variable(mocker,
                                                                    monkeypatch):
    #Arrange
    get_document_intelligence_settings.cache_clear()
    set_mock_logger_builder(mocker)

    monkeypatch.setenv('DOCUMENT_INTELLIGENCE_KEY', 'key')
    req_body = {
        "values":[
            {
                "recordId":"",
                "data":""
            }
        ]
    }
    req = func.HttpRequest(method='POST',
                        headers={'Content-Type':'application/json'},
                        body=bytes(json.dumps(req_body), "utf-8"),
                        url='/api/documentIntelligence',
                        params={'outputFormat': 'markdown'})
    mock_trace_context = mocker.Mock()
    #Act
    func_call = document_intelligence.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    #Assert
    assert response.status_code == 500