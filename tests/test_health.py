import json
import pytest
from unittest.mock import AsyncMock
import azure.functions as func
from health_check import health_check as health_check_endpoint
from tests.mock_logging import set_mock_logger_builder


def set_mock_env(monkeypatch):
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING",
                       "myAPPLICATIONINSIGHTS_CONNECTION_STRING")
    monkeypatch.setenv("AZURE_MISTRALAI_ENDPOINT",
                       "myAZURE_MISTRALAI_ENDPOINT")
    monkeypatch.setenv("AZURE_MISTRALAI_KEY", "myAZURE_MISTRALAI_KEY")
    monkeypatch.setenv("AZURE_MISTRALAI_TEMPERATURE", "0")
    monkeypatch.setenv("AZURE_MISTRALAI_TOKENS", "2000")
    monkeypatch.setenv("AZURE_MISTRALAI_MODEL", "myAZURE_MISTRALAI_MODEL")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION",
                       "myAZURE_OPENAI_API_VERSION")
    monkeypatch.setenv("AZURE_OPENAI_COMPLETION_TOKENS", "2000")
    monkeypatch.setenv("AZURE_OPENAI_COMPLETION_ENDPOINT",
                       "myAZURE_OPENAI_COMPLETION_ENDPOINT")
    monkeypatch.setenv("AZURE_OPENAI_COMPLETION_TEMPERATURE", "0")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_MODEL",
                       "myAZURE_OPENAI_EMBEDDING_DEPLOYMENT_MODEL")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_ENDPOINT",
                       "myAZURE_OPENAI_EMBEDDING_ENDPOINT")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_KEY", "myKey")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_MODEL",
                       "myAZURE_OPENAI_DEPLOYMENT_MODEL")
    monkeypatch.setenv("AZURE_OPENAI_KEY", "myAZURE_OPENAI_KEY")
    monkeypatch.setenv("AZURE_SEARCH_API_VERSION",
                       "myAZURE_SEARCH_API_VERSION")
    monkeypatch.setenv("AZURE_SEARCH_ENDPOINT", "myAZURE_SEARCH_ENDPOINT")
    monkeypatch.setenv("AZURE_SEARCH_INDEX", "myAZURE_SEARCH_INDEX")
    monkeypatch.setenv("AZURE_SEARCH_INDEX_SEMANTIC_CONFIGURATION",
                       "myAZURE_SEARCH_INDEX_SEMANTIC_CONFIGURATION")
    monkeypatch.setenv("AZURE_SEARCH_K", "0")
    monkeypatch.setenv("AZURE_SEARCH_KEY", "myAZURE_SEARCH_KEY")
    monkeypatch.setenv("ENRICHMENT_ENDPOINT", "myENRICHMENT_ENDPOINT")
    monkeypatch.setenv("QUERY_ENDPOINT", "myQUERY_ENDPOINT")
    monkeypatch.setenv("CQA_Endpoint", "myCQA_Endpoint")
    monkeypatch.setenv("CQA_KeyCredential", "myCQA_KeyCredential")
    monkeypatch.setenv("CQA_KnowledgeBaseProject",
                       "myCQA_KnowledgeBaseProject")
    monkeypatch.setenv("CQA_Deployment", "myCQA_Deployment")
    monkeypatch.setenv("CQA_DefaultNoResultAnswer", "Nessuna risposta trovata")
    monkeypatch.setenv("CQA_ConfidenceThreshold", "0.25")
    monkeypatch.setenv("Enrichment_SystemTemplatePath",
                       "myEnrichment_SystemTemplatePath")
    monkeypatch.setenv("Enrichment_UserTemplatePath",
                       "myEnrichment_UserTemplatePath")
    monkeypatch.setenv("Enrichment_TagsFilePath", "myEnrichment_TagsFilePath")
    monkeypatch.setenv("STORAGE_CONNECTION_STRING",
                       "mySTORAGE_CONNECTION_STRING")
    monkeypatch.setenv("STORAGE_PROMPT_CONTAINER",
                       "mySTORAGE_PROMPT_CONTAINER")
    monkeypatch.setenv('DOCUMENT_INTELLIGENCE_KEY', 'key')
    monkeypatch.setenv('DOCUMENT_INTELLIGENCE_ENDPOINT', 'endpoint')
    monkeypatch.setenv(
        "AZURE_KEY_VAULT_SECRET_MAP_CONTAINER_NAME", "container")
    monkeypatch.setenv("AZURE_KEY_VAULT_SECRET_MAP_FILE_NAME", "file")
    monkeypatch.setenv("AZURE_KEY_VAULT_URL", "url")


@pytest.mark.asyncio
async def test_health_check(mocker,
                            monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)

    set_mock_logger_builder(mocker)

    req_body = {
        "tags": []
    }
    req = func.HttpRequest(method='POST',
                           headers={
                               'Content-Type': 'application/json',
                               'caller-service': 'test-service'
                           },
                           body=bytes(json.dumps(req_body), "utf-8"),
                           url='/api/health')
    mock_trace_context = mocker.Mock()
    # Act
    func_call = health_check_endpoint.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    # Assert
    assert response.status_code == 200

    # Assert the mimetype
    assert response.mimetype == "application/json"
