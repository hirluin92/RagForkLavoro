import json
import os
import azure.functions as func
import pytest
import logics
from logics.ai_query_service_base import AiQueryServiceBase
from logics.ai_query_service_factory import AiQueryServiceFactory
import logics.rag_orchestrator
import logics.rag_query

from models.apis.enrichment_query_response import EnrichmentQueryResponse
from models.apis.rag_orchestrator_request import RagOrchestratorRequest
from models.apis.rag_orchestrator_response import RagOrchestratorResponse
from models.apis.rag_query_response_body import RagQueryResponse
import services
from services.ai_query_service_mistralai import AiQueryServiceMistralAI
from services.ai_query_service_openai import AiQueryServiceOpenAI
from services.logging import Logger
from tests.mock_logging import MockLogger, set_mock_logger_builder
from rag_augment_query import a_augment_query as  rag_augmentQuery_endpoint
from services.cqa import a_do_query
import constants.llm as llm_constants

def set_mock_env(monkeypatch):
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING" , "myAPPLICATIONINSIGHTS_CONNECTION_STRING")
    monkeypatch.setenv("AZURE_MISTRALAI_ENDPOINT" , "myAZURE_MISTRALAI_ENDPOINT")
    monkeypatch.setenv("AZURE_MISTRALAI_KEY" , "myAZURE_MISTRALAI_KEY")
    monkeypatch.setenv("AZURE_MISTRALAI_TEMPERATURE" , "0")
    monkeypatch.setenv("AZURE_MISTRALAI_TOKENS" , "2000")
    monkeypatch.setenv("AZURE_MISTRALAI_MODEL" , "myAZURE_MISTRALAI_MODEL")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION" , "myAZURE_OPENAI_API_VERSION")
    monkeypatch.setenv("AZURE_OPENAI_COMPLETION_TOKENS" , "2000")
    monkeypatch.setenv("AZURE_OPENAI_COMPLETION_ENDPOINT" , "myAZURE_OPENAI_COMPLETION_ENDPOINT")
    monkeypatch.setenv("AZURE_OPENAI_COMPLETION_KEY" , "key")
    monkeypatch.setenv("AZURE_OPENAI_COMPLETION_TEMPERATURE" , "0")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_MODEL" , "myAZURE_OPENAI_EMBEDDING_DEPLOYMENT_MODEL")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_ENDPOINT" , "myAZURE_OPENAI_EMBEDDING_ENDPOINT")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_KEY" , "key")
    monkeypatch.setenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_MODEL" , "myAZURE_OPENAI_DEPLOYMENT_MODEL")
    monkeypatch.setenv("AZURE_SEARCH_API_VERSION" , "myAZURE_SEARCH_API_VERSION")
    monkeypatch.setenv("AZURE_SEARCH_ENDPOINT" , "myAZURE_SEARCH_ENDPOINT")
    monkeypatch.setenv("AZURE_SEARCH_INDEX" , "myAZURE_SEARCH_INDEX")
    monkeypatch.setenv("AZURE_SEARCH_INDEX_SEMANTIC_CONFIGURATION" , "myAZURE_SEARCH_INDEX_SEMANTIC_CONFIGURATION")
    monkeypatch.setenv("AZURE_SEARCH_K" , "0")
    monkeypatch.setenv("AZURE_SEARCH_KEY" , "myAZURE_SEARCH_KEY")
    monkeypatch.setenv("ENRICHMENT_ENDPOINT" , "myENRICHMENT_ENDPOINT")
    monkeypatch.setenv("QUERY_ENDPOINT" , "myQUERY_ENDPOINT")
    monkeypatch.setenv("CQA_Endpoint" , "myCQA_Endpoint")
    monkeypatch.setenv("CQA_KeyCredential" , "myCQA_KeyCredential")
    monkeypatch.setenv("CQA_KnowledgeBaseProject" , "myCQA_KnowledgeBaseProject")
    monkeypatch.setenv("CQA_Deployment" , "myCQA_Deployment")
    monkeypatch.setenv("CQA_DefaultNoResultAnswer" , "Nessuna risposta trovata")
    monkeypatch.setenv("CQA_ConfidenceThreshold" , "0.25")
    monkeypatch.setenv('STORAGE_BULK_SPLIT_FILES_CONTAINER', 'container')
    monkeypatch.setenv('STORAGE_DATA_SOURCE_SPLIT_FILES_CONTAINER', 'container')
    monkeypatch.setenv('STORAGE_CONNECTION_STRING', 'connection_string')
    monkeypatch.setenv('STORAGE_PROMPT_FILES_CONTAINER', 'container')
    monkeypatch.setenv('STORAGE_UPLOADED_FILES_CONTAINER', 'container')
    monkeypatch.setenv('STORAGE_UPLOADED_SPLIT_FILES_CONTAINER', 'container')

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
        "llm_model_id": llm_constants.openai,
        "interactions": [{ "question": "fake", "answer": "fake" }]
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
    