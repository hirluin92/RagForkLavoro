import json
import os
import azure.functions as func
import pytest
import logics
from logics.ai_query_service_base import AiQueryServiceBase
from logics.ai_query_service_factory import AiQueryServiceFactory
import logics.rag_orchestrator
from models.apis.rag_orchestrator_request import RagOrchestratorRequest
from models.apis.rag_orchestrator_response import RagOrchestratorResponse
from models.apis.rag_query_response_body import RagQueryResponse
from models.services.cqa_response import CQAResponse
from services.ai_query_service_mistralai import AiQueryServiceMistralAI
from services.ai_query_service_openai import AiQueryServiceOpenAI
from services.logging import Logger
from tests.mock_env import set_mock_env
from tests.mock_logging import set_mock_logger_builder
from rag_orchestrator import a_rag_orchestrator as ragOrchestrator_endpoint
from services.cqa import a_do_query
import constants.llm as llm_constants
from utils.settings import (
    get_cqa_settings,
    get_mistralai_settings,
    get_openai_settings, 
    get_search_settings, 
    get_storage_settings
    )

@pytest.mark.asyncio
async def test_query_no_body(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)

    set_mock_logger_builder(mocker)

    req = func.HttpRequest(method='POST',
                           headers={'Content-Type': 'application/json'},
                           body=None,
                           url='/api/ragOrchestrator')

    mock_trace_context = mocker.Mock()

    # Act
    func_call = ragOrchestrator_endpoint.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    # Assert
    assert response.status_code == 500

@pytest.mark.asyncio
async def test_query_missing_environment_variables(mocker):
    # Arrange
    get_cqa_settings.cache_clear()
    get_mistralai_settings.cache_clear()
    get_openai_settings.cache_clear()
    get_search_settings.cache_clear()
    get_storage_settings.cache_clear()

    set_mock_logger_builder(mocker)

    req_body = {
        "question": "question",
        "tags": ["auu"]
    }
    req = func.HttpRequest(method='POST',
                           headers={'Content-Type': 'application/json'},
                           body=bytes(json.dumps(req_body), "utf-8"),
                           url='/api/ragOrchestrator')

    mock_trace_context = mocker.Mock()
    # Act
    func_call = ragOrchestrator_endpoint.build().get_user_function()
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
        "tags": ["auu"]
    }
    req = func.HttpRequest(method='POST',
                           headers={'Content-Type': 'application/json'},
                           body=bytes(json.dumps(req_body), "utf-8"),
                           url='/api/ragOrchestrator')
    mock_trace_context = mocker.Mock()
    # Act
    func_call = ragOrchestrator_endpoint.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    # Assert
    assert response.status_code == 422

@pytest.mark.asyncio  
async def test_cqa_answer_hi_confidence(mocker, monkeypatch):
    
    set_mock_env(monkeypatch)

    query = "Cos'è l'assegno unico?"
    logger = mocker.Mock(spec=Logger)

    cqa_mock_response = mocker.Mock()
    cqa_mock_response.answers = [mocker.Mock(answer="L'assegno unico è...", confidence=0.8)]
    cqa_mock_response.serialize.return_value = "{ 'fake' : 'fake' }"
    cqa_mock_client = mocker.AsyncMock()
    cqa_mock_client.get_answers.return_value = cqa_mock_response
    mocker.patch('services.cqa.get_question_answering_client', return_value=cqa_mock_client)

    result = await a_do_query(query, "", logger)

    assert result.text_answer 
    assert result.text_answer != str(os.getenv("default_noresult_answer"))
    assert isinstance(result, CQAResponse)
    logger.track_event.assert_called_once()

@pytest.mark.asyncio   
async def test_cqa_answer_low_confidence(mocker, monkeypatch):
    
    set_mock_env(monkeypatch)

    query = "Cos'è l'assegno unico?"
    logger = mocker.Mock(spec=Logger)

    cqa_mock_response = mocker.Mock()
    cqa_mock_response.answers = [mocker.Mock(answer="La pensione...", confidence=0.1)]
    cqa_mock_response.serialize.return_value = "{ 'fake' : 'fake' }"
    cqa_mock_client = mocker.AsyncMock() 
    cqa_mock_client.get_answers.return_value = cqa_mock_response
    mocker.patch('services.cqa.get_question_answering_client', return_value=cqa_mock_client)

    result = await a_do_query(query, "", logger)

    assert result == None
    logger.track_event.assert_called_once()
    
@pytest.mark.asyncio 
async def test_cqa_answer_out_of_context(mocker, monkeypatch):
    
    set_mock_env(monkeypatch)

    query = "Come è il tempo?"
    logger = mocker.Mock(spec=Logger)

    mock_response = mocker.Mock()
    mock_response.answers = [mocker.Mock(answer = os.getenv("CQA_DefaultNoResultAnswer"), confidence=0.1)]
    mock_response.serialize.return_value = "{ 'fake' : 'fake' }"
    cqa_mock_client = mocker.AsyncMock() 
    cqa_mock_client.get_answers.return_value = mock_response
    mocker.patch('services.cqa.get_question_answering_client', return_value = cqa_mock_client)

    result = await a_do_query(query, "", logger)

    assert result == None
    logger.track_event.assert_called_once()

@pytest.mark.asyncio  
async def test_rag_orchestrator_cqa_success(mocker, monkeypatch):
    set_mock_env(monkeypatch)
    logger = mocker.Mock(spec=Logger)
    mock_session = mocker.Mock()
    
    mock_cqa_do_query_result = CQAResponse(text_answer="L'assegno unico è...", cqa_data={ "fake" : "fake"})
    mocker.patch('logics.rag_orchestrator.cqa_do_query', return_value=mock_cqa_do_query_result)
    
    request = RagOrchestratorRequest(query="Cosa è l'assegno unico?", llm_model_id="OPENAI", tags= ["auu"])
    result = await logics.rag_orchestrator.a_get_query_response(request, logger, mock_session)
    
    assert isinstance(result, RagOrchestratorResponse)
    assert result.answer_text
    assert result.cqa_data
    assert result.llm_data == None
    
@pytest.mark.asyncio
async def test_get_query_response_cqa_fail_then_succeed(mocker,monkeypatch):
    set_mock_env(monkeypatch)
    logger = mocker.Mock(spec=Logger)
    mock_session = mocker.Mock()

    test_rag_orchestrator_response = CQAResponse(text_answer="L'assegno unico è...", cqa_data={ "fake" : "fake"})
    mocker.patch('logics.rag_orchestrator.cqa_do_query', side_effect=[None, test_rag_orchestrator_response])
    
    mock_language_service = mocker.Mock(spec=AiQueryServiceBase)
    mock_language_service.a_do_query_enrichment.return_value = mocker.Mock(standalone_question="Cos'è l'assegno unico?",
                                                                                       end_conversation=False)
    mocker.patch('logics.ai_query_service_factory.AiQueryServiceFactory.get_instance', return_value=mock_language_service)
    
    request = RagOrchestratorRequest(query="Aseno unco", llm_model_id="OPENAI", interactions= [ { "question": "fake", "answer": "fake" } ], tags= ["auu"])
    result = await logics.rag_orchestrator.a_get_query_response(request, logger, mock_session)
    
    assert isinstance(result, RagOrchestratorResponse)
    assert result.answer_text
    assert result.cqa_data
    assert result.llm_data == None
    mock_language_service.a_do_query_enrichment.assert_called_once_with(request, logger)
    
@pytest.mark.asyncio
async def test_get_query_response_cqa_fail_twice_then_llm_succeed(mocker, monkeypatch):
    set_mock_env(monkeypatch)
    logger = mocker.Mock(spec=Logger)
    mock_session = mocker.Mock()
    
    mocker.patch('logics.rag_orchestrator.cqa_do_query', return_value = None)
    
    mock_language_service = mocker.Mock(spec=AiQueryServiceBase)
    mock_language_service.a_do_query_enrichment.return_value = mocker.Mock(standalone_question="Cos'è l'assegno unico?",
                                                                                       end_conversation= False)
    mock_language_service.a_do_query.return_value = RagQueryResponse("L'assegno unico è un ....",[], "stop", None, None, None, None, None)
    mocker.patch('logics.ai_query_service_factory.AiQueryServiceFactory.get_instance', return_value=mock_language_service)
    
    request = RagOrchestratorRequest(query="Aseno unco", llm_model_id="OPENAI", interactions= [ { "question": "fake", "answer": "fake" } ], tags= ["auu"])
    result = await logics.rag_orchestrator.a_get_query_response(request, logger,mock_session)
    
    assert isinstance(result, RagOrchestratorResponse)
    assert result.answer_text
    assert result.cqa_data == None
    assert result.llm_data 
    mock_language_service.a_do_query_enrichment.assert_called_once_with(request, logger)
    
def test_factory():
    
    result = AiQueryServiceFactory.get_instance(llm_constants.openai)
    assert result
    assert isinstance(result, AiQueryServiceOpenAI)
    
    result = AiQueryServiceFactory.get_instance(llm_constants.mistralai)
    assert result
    assert isinstance(result, AiQueryServiceMistralAI)
    
    result = AiQueryServiceFactory.get_instance("FAKE")
    assert result
    assert isinstance(result, AiQueryServiceOpenAI)