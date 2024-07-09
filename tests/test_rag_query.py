import json
import azure.functions as func
import pytest
from logics.rag_query import (
    build_question_context_from_search,
    build_response_for_user,
    a_execute_query)
from rag_query import a_query as rag_query_endpoint
from services.search import a_query
from tests.mock_aiohttp import MockClientResponse, MockClientSession
from tests.mock_env import set_mock_env
from tests.mock_logging import MockLogger, set_mock_logger_builder
import constants.llm as llm_const
from utils.settings import (
    get_mistralai_settings,
    get_openai_settings,
    get_search_settings,
    get_storage_settings
    )

def test_build_response_for_user_rag_response_empty(mocker):
    # Arrange
    mock_rag_response = mocker.Mock()
    mock_rag_response.references = []

    # Act
    result = build_response_for_user(mock_rag_response, [])

    # Assert
    assert len(result) > 0
    assert result[0] == "Mi dispiace, non riesco a fornire una risposta alla tua domanda."

def test_build_response_for_user_rag_response_invalid_references(mocker):
    # Arrange
    mock_rag_response = mocker.Mock()
    mock_rag_response.references = [1]

    mock_reference = mocker.Mock()
    mock_reference.reference = 2

    mock_context = mocker.Mock()
    mock_context = [mock_reference]

    # Act
    # Assert
    with pytest.raises(Exception):
        build_response_for_user(mock_rag_response, mock_context)

def test_build_response_for_user_ok(mocker):
    # Arrange
    mock_rag_response = mocker.Mock()
    mock_rag_response.response = "LLM response"
    mock_rag_response.references = [1]

    mock_reference = mocker.Mock()
    mock_reference.reference = 1
    mock_reference.filename = "reference.txt"

    mock_context = mocker.Mock()
    mock_context = [mock_reference]

    # Act
    result = build_response_for_user(mock_rag_response, mock_context)

    # Assert
    assert len(result) > 0
    assert "LLM response" in result[0]
    assert "reference.txt" in result[1]

def test_build_question_context_from_search_empty_context(mocker):
    # Arrange
    mock_search_result = mocker.Mock()
    mock_search_result.value = []

    # Act
    result = build_question_context_from_search(mock_search_result, 0)

    # Assert
    assert len(result) == 0

def test_build_question_context_from_search_ok(mocker):
    # Arrange
    mock_search_result_value = mocker.Mock()
    mock_search_result_value.chunk_id = "chunk_id"
    mock_search_result_value.chunk_text = "chunk_text"
    mock_search_result_value.filename = "filename"
    mock_search_result_value.search_captions = [mocker.Mock(text="caption")]
    mock_search_result_value.search_rerankerScore = 2
    mock_search_result_value.tags = ["auu"]

    mock_search_result = mocker.Mock()
    mock_search_result.value = [mock_search_result_value]

    # Act
    result = build_question_context_from_search(mock_search_result, 0)

    # Assert
    assert len(result) == 1
    assert result[0].chunk_id == "chunk_id"
    assert result[0].chunk == "chunk_text"
    assert result[0].filename == "filename"
    assert result[0].caption == "caption"
    assert result[0].score == 2
    assert result[0].reference == 1
    assert result[0].tags == "auu"

@pytest.mark.asyncio
async def test_get_from_index_ko(mocker, monkeypatch):
    # Arrange
    mock_logger = MockLogger()
    set_mock_env(monkeypatch)

    question = "question"
    tags = ["tag"]

    mocker.patch("aiohttp.ClientSession.post",
                 side_effect=Exception)

    # Act
    # Assert
    with pytest.raises(Exception):
        await a_query(question, [1], tags, mock_logger)

@pytest.mark.asyncio
async def test_get_from_index_ok(mocker,
                                 monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)

    mock_logger = MockLogger()

    question = "question"
    tags = ["tag"]

    mock_response_json_answer = {
        "key": "key",
        "text": "text",
        "highlights": "highlights",
        "score": 1
    }
    mock_response_json_value = {
        "@search.score": 1,
        "@search.rerankerScore": 2,
        "@search.captions": [{"text": "text", "highlights": "highlights"}],
        "chunk_id": "chunk_id",
        "chunk_text": "chunk_text",
        "filename": "filename",
        "tags": ["tag"],
    }
    response_data = {
        "@odata.context": "context",
        "@odata.count": 1,
        "@search.answers": [mock_response_json_answer],
        "value": [mock_response_json_value]
    }
    mock_response = MockClientResponse(response_data,200)
    mock_session = MockClientSession(mock_response)

    # Act
    result = await a_query(mock_session,question, [], tags, mock_logger)
    # Assert
    assert result.data_context == "context"
    assert result.data_count == 1
    assert len(result.search_answers) == 1
    assert len(result.value) == 1

@pytest.mark.asyncio
async def test_execute_query_empty_search_results_ok(mocker):
    # Arrange
    mock_logger = MockLogger()

    mock_embedding = mocker.Mock()
    mocker.patch(
        "logics.rag_query.openai_generate_embedding_from_text",
        return_value=mock_embedding
    )

    mock_search_result = mocker.Mock()
    mock_search_result.value = []
    
    mocker.patch(
        "logics.rag_query.query_azure_ai_search",
        return_value=mock_search_result
    )
    mock_session = mocker.Mock()
    # Act
    result = await a_execute_query("llm", "query", ["auu"], mock_logger, mock_session)
    # Arrange
    assert result.response == llm_const.default_answer
    assert len(result.links) == 0
    assert result.finish_reason == ""

@pytest.mark.asyncio
async def test_execute_query_mistralai_ok(mocker,monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)

    mock_logger = MockLogger()

    mock_embedding = mocker.Mock()
    mocker.patch(
        "logics.rag_query.openai_generate_embedding_from_text",
        return_value=mock_embedding
    )

    mock_caption = mocker.Mock()
    mock_caption.text = "text"
    mock_search_result = mocker.Mock()
    mock_search_result.value = [mocker.Mock(chunk_id="id",
                                            chunk_text="text",
                                            filename="filename",
                                            search_captions=[mock_caption],
                                            search_rerankerScore=1,
                                            tags=["auu"])]
    mocker.patch(
        "logics.rag_query.query_azure_ai_search",
        return_value=mock_search_result
    )

    mocker.patch(
        "logics.rag_query.a_get_blob_content_from_container",
        side_effect=["SYSTEM_PROMPT", "USER_PROMPT", "SYSTEM_LINKS_PROMPT"]
    )

    mock_rag_response = mocker.Mock()
    mock_rag_response.response = "query answer"
    mock_rag_response.finish_reason = "stop"
    mock_rag_response.references = [1]
    mocker.patch(
        "logics.rag_query.mistralai_get_answer_from_context",
        return_value=mock_rag_response
    )
    mock_session = mocker.Mock()
    # Act
    result = await a_execute_query(llm_const.mistralai, "query", ["auu"], mock_logger,mock_session)
    # Arrange
    assert result.response == "query answer"
    assert len(result.links) == 1
    assert result.finish_reason == "stop"

@pytest.mark.asyncio
async def test_execute_query_openai_ok(mocker,monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)

    mock_logger = MockLogger()

    mock_embedding = mocker.Mock()
    mocker.patch(
        "logics.rag_query.openai_generate_embedding_from_text",
        return_value=mock_embedding
    )

    mock_caption = mocker.Mock()
    mock_caption.text = "text"
    mock_search_result = mocker.Mock()
    mock_search_result.value = [mocker.Mock(chunk_id="id",
                                            chunk_text="text",
                                            filename="filename",
                                            search_captions=[mock_caption],
                                            search_rerankerScore=1,
                                            tags=["auu"])]
    mocker.patch(
        "logics.rag_query.query_azure_ai_search",
        return_value=mock_search_result
    )

    mocker.patch(
        "logics.rag_query.a_get_blob_content_from_container",
        side_effect=["SYSTEM_PROMPT", "USER_PROMPT", "SYSTEM_LINKS_PROMPT"]
    )

    mock_rag_response = mocker.Mock()
    mock_rag_response.response = "query answer"
    mock_rag_response.finish_reason = "stop"
    mock_rag_response.references = [1]
    mocker.patch(
        "logics.rag_query.openai_get_answer_from_context",
        return_value=mock_rag_response
    )
    mock_session = mocker.Mock()
    # Act
    result = await a_execute_query(llm_const.openai, "query", ["auu"], mock_logger,mock_session)
    # Arrange
    assert result.response == "query answer"
    assert len(result.links) == 1
    assert result.finish_reason == "stop"

@pytest.mark.asyncio
async def test_query_ok(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)

    set_mock_logger_builder(mocker)

    req_body = {
        "query": "query",
        "llm_model_id": "model",
        "tags": []
    }

    mock_result = mocker.Mock()
    mock_result.toJSON.return_value = '{"response": "answer"}'

    mock_language_service = mocker.AsyncMock()
    mock_language_service.a_do_query.return_value = mock_result
    mocker.patch(
        "rag_query.AiQueryServiceFactory.get_instance",
         return_value=mock_language_service
    )

    req = func.HttpRequest(method='POST',
                           headers={'Content-Type': 'application/json'},
                           body=bytes(json.dumps(req_body), "utf-8"),
                           url='/api/query',
                           params={'outputFormat': 'markdown'})

    mock_trace_context = mocker.Mock()

    # Act
    func_call = rag_query_endpoint.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    # Assert
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_query_ko(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)

    set_mock_logger_builder(mocker)

    req_body = {
        "query": "query",
        "llm_model_id": "model",
        "tags": []
    }

    mock_language_service = mocker.Mock()
    mock_language_service.a_do_query.side_effect = Exception("Error")
    mocker.patch(
        "rag_query.AiQueryServiceFactory.get_instance",
         return_value=mock_language_service
    )

    req = func.HttpRequest(method='POST',
                           headers={'Content-Type': 'application/json'},
                           body=bytes(json.dumps(req_body), "utf-8"),
                           url='/api/query',
                           params={'outputFormat': 'markdown'})

    mock_trace_context = mocker.Mock()

    # Act
    func_call = rag_query_endpoint.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    # Assert
    assert response.status_code == 500

@pytest.mark.asyncio
async def test_query_no_body(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)

    set_mock_logger_builder(mocker)

    req = func.HttpRequest(method='POST',
                           headers={'Content-Type': 'application/json'},
                           body=None,
                           url='/api/query',
                           params={'outputFormat': 'markdown'})

    mock_trace_context = mocker.Mock()

    # Act
    func_call = rag_query_endpoint.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    # Assert
    assert response.status_code == 500

@pytest.mark.asyncio
async def test_query_missing_environment_variables(mocker):
    # Arrange
    get_mistralai_settings.cache_clear()
    get_openai_settings.cache_clear()
    get_search_settings.cache_clear()
    get_storage_settings.cache_clear()

    set_mock_logger_builder(mocker)

    req_body = {
        "question": "question",
        "tags": []
    }
    req = func.HttpRequest(method='POST',
                           headers={'Content-Type': 'application/json'},
                           body=bytes(json.dumps(req_body), "utf-8"),
                           url='/api/query')

    mock_trace_context = mocker.Mock()
    # Act
    func_call = rag_query_endpoint.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    # Assert
    assert response.status_code == 500

@pytest.mark.asyncio
async def test_query_missing_body_value_question(mocker,
                                           monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)

    set_mock_logger_builder(mocker)

    req_body = {
        "tags": []
    }
    req = func.HttpRequest(method='POST',
                           headers={'Content-Type': 'application/json'},
                           body=bytes(json.dumps(req_body), "utf-8"),
                           url='/api/query')
    mock_trace_context = mocker.Mock()
    # Act
    func_call = rag_query_endpoint.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    # Assert
    assert response.status_code == 422
