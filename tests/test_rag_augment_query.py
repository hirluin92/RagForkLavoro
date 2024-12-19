import json
import azure.functions as func
import pytest

from models.apis.prompt_editor_response_body import PromptEditorResponseBody
from models.apis.rag_orchestrator_request import RagOrchestratorRequest
from tests.mock_env import set_mock_env
from tests.mock_logging import set_mock_logger_builder
from rag_augment_query import a_augment_query as  rag_augmentQuery_endpoint
import constants.llm as llm_constants


@pytest.mark.asyncio
async def test_query_no_body(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)

    set_mock_logger_builder(mocker)

    req = func.HttpRequest(method='POST',
                           headers={'Content-Type': 'application/json'},
                           body=None,
                           url='/api/augmentQuery')

    mock_trace_context = mocker.Mock()

    # Act
    func_call = rag_augmentQuery_endpoint.build().get_user_function()
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
                           url='/api/augmentQuery')
    mock_trace_context = mocker.Mock()
    # Act
    func_call = rag_augmentQuery_endpoint.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    # Assert
    assert response.status_code == 422
    
@pytest.mark.asyncio
async def test_query_success(mocker, monkeypatch):
    
    # Arrange
    set_mock_env(monkeypatch)
    set_mock_logger_builder(mocker)
    mock_trace_context = mocker.Mock()
    
    mock_prompt_data = PromptEditorResponseBody(version = '1',
                                                    llm_model='OPENAI',
                                                    prompt = [],
                                                    parameters=[],
                                                    model_parameters= None)
    mocker.patch('rag_augment_query.a_get_enrichment_prompt_data', return_value = mock_prompt_data)

    mock_result = mocker.Mock(standalone_question="answer",end_conversation=False)
    mock_result.model_dump.return_value= {"standalone_question": "answer"}

    mock_language_service = mocker.AsyncMock()
    mock_language_service.a_do_query_enrichment.return_value = mock_result
    mocker.patch(
        "rag_augment_query.AiQueryServiceFactory.get_instance",
         return_value=mock_language_service
    )
    
    req_body = {
        "query": "Aseno unco",
        "llm_model_id": "OPENAI",
        "interactions": [{ "question": "fake", "answer": "fake" }],
        "environment":"staging",
        "prompt_editor": []
    }

    req = func.HttpRequest(method='POST',
                           headers={'Content-Type': 'application/json'},
                           body=bytes(json.dumps(req_body), "utf-8"),
                           url='/api/augmentQuery')
    # Act
    func_call = rag_augmentQuery_endpoint.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    # Assert
    assert response.status_code == 200
    