import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import azure.functions as func
from pydantic import ValidationError
import pytest
import logics
from tests.mock_env import set_mock_env
from logics.ai_query_service_base import AiQueryServiceBase
from logics.ai_query_service_factory import AiQueryServiceFactory
import logics.rag_orchestrator
from models.apis.prompt_editor_response_body import PromptEditorResponseBody
from models.apis.rag_orchestrator_request import RagConfiguration, RagOrchestratorRequest
from models.apis.rag_orchestrator_response import RagOrchestratorResponse
from models.apis.rag_query_response_body import RagQueryResponse
from models.services.cqa_response import CQAResponse
from services.ai_query_service_mistralai import AiQueryServiceMistralAI
from services.ai_query_service_openai import AiQueryServiceOpenAI
from models.apis.rag_orchestrator_request import RagOrchestratorRequest, Interaction
from models.apis.prompt_editor_response_body import PromptEditorResponseBody
from models.apis.rag_query_response_body import RagQueryResponse
from models.apis.enrichment_query_response import EnrichmentQueryResponse
from models.services.openai_intent_response import ClassifyIntentResponse
from models.services.openai_domus_response import DomusAnswerResponse
from services.logging import Logger
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
async def test_query_no_configuration(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)
    set_mock_logger_builder(mocker)
    req = func.HttpRequest(method='POST',
                           headers={'Content-Type': 'application/json'},
                           body=None,
                           url='/api/ragOrchestrator')

    mock_trace_context = mocker.Mock()    
    mocker.patch('utils.settings.get_openai_settings', side_effect = ValidationError)

    # Act
    func_call = ragOrchestrator_endpoint.build().get_user_function()
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
                           url='/api/ragOrchestrator')

    mock_trace_context = mocker.Mock()

    # Act
    func_call = ragOrchestrator_endpoint.build().get_user_function()
    response = await func_call(req, mock_trace_context)
    # Assert
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_query_missing_environment_variables(mocker, monkeypatch):
    set_mock_env(monkeypatch)
    
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
    assert response.status_code == 422


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
    cqa_mock_response.answers = [mocker.Mock(
        answer="L'assegno unico è...", confidence=0.8)]
    cqa_mock_response.serialize.return_value = "{ 'fake' : 'fake' }"
    cqa_mock_client = mocker.AsyncMock()
    cqa_mock_client.get_answers.return_value = cqa_mock_response
    mocker.patch('services.cqa.get_question_answering_client',
                 return_value=cqa_mock_client)

    # Mock del metodo a_get_cqa_project_by_topic
    mocker.patch('services.cqa.a_get_cqa_project_by_topic',
                 return_value=("mock_project", "mock_deployment"))

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
    cqa_mock_response.answers = [mocker.Mock(
        answer="La pensione...", confidence=0.1)]
    cqa_mock_response.serialize.return_value = "{ 'fake' : 'fake' }"
    cqa_mock_client = mocker.AsyncMock()
    cqa_mock_client.get_answers.return_value = cqa_mock_response
    mocker.patch('services.cqa.get_question_answering_client',
                 return_value=cqa_mock_client)

    # Mock del metodo a_get_cqa_project_by_topic
    mocker.patch('services.cqa.a_get_cqa_project_by_topic',
                 return_value=("mock_project", "mock_deployment"))

    result = await a_do_query(query, "", logger)

    assert result == None
    logger.track_event.assert_called_once()


@pytest.mark.asyncio
async def test_cqa_answer_out_of_context(mocker, monkeypatch):

    set_mock_env(monkeypatch)

    query = "Come è il tempo?"
    logger = mocker.Mock(spec=Logger)

    mock_response = mocker.Mock()
    mock_response.answers = [mocker.Mock(answer=os.getenv(
        "CQA_DefaultNoResultAnswer"), confidence=0.1)]
    mock_response.serialize.return_value = "{ 'fake' : 'fake' }"
    cqa_mock_client = mocker.AsyncMock()
    cqa_mock_client.get_answers.return_value = mock_response
    mocker.patch('services.cqa.get_question_answering_client',
                 return_value=cqa_mock_client)

    # Mock del metodo a_get_cqa_project_by_topic
    mocker.patch('services.cqa.a_get_cqa_project_by_topic',
                 return_value=("mock_project", "mock_deployment"))

    result = await a_do_query(query, "", logger)

    assert result == None
    logger.track_event.assert_called_once()


# ---------------------------------------
# Fake classes per simulare il comportamento di aioodbc
# ---------------------------------------

class FakePoolContextManager:
    """Simula il context manager restituito da create_pool."""
    def __init__(self, fake_cursor):
        self.fake_cursor = fake_cursor

    async def __aenter__(self):
        return FakePool(self.fake_cursor)

    async def __aexit__(self, exc_type, exc, tb):
        pass

class FakePool:
    """Simula il pool (il quale ha il metodo acquire())."""
    def __init__(self, fake_cursor):
        self.fake_cursor = fake_cursor

    def acquire(self):
        return FakeConnectionContextManager(self.fake_cursor)

class FakeConnectionContextManager:
    """Simula il context manager restituito dal metodo acquire()."""
    def __init__(self, fake_cursor):
        self.fake_cursor = fake_cursor

    async def __aenter__(self):
        return FakeConnection(self.fake_cursor)

    async def __aexit__(self, exc_type, exc, tb):
        pass

class FakeConnection:
    """Simula la connessione (il quale ha il metodo cursor())."""
    def __init__(self, fake_cursor):
        self.fake_cursor = fake_cursor

    def cursor(self):
        return FakeCursorContextManager(self.fake_cursor)

class FakeCursorContextManager:
    """Simula il context manager per il cursore."""
    def __init__(self, fake_cursor):
        self.fake_cursor = fake_cursor

    async def __aenter__(self):
        return self.fake_cursor

    async def __aexit__(self, exc_type, exc, tb):
        pass

class FakeCursor:
    """
    Fake del cursore usato per:
      - eseguire le query (il metodo execute)
      - simulare il fetchall() (per a_get_tags_by_tag_names e a_check_status_tag_for_mst)
      - oppure l'iterazione asincrona (per a_get_prompt_info)
    """
    def __init__(self, fetchall_return=None, iter_records=None):
        self.fetchall_return = fetchall_return
        self.iter_records = iter_records if iter_records is not None else []
        self.executed_sql = None
        self.executed_params = None

    async def execute(self, sql, params=None):
        self.executed_sql = sql
        self.executed_params = params

    async def fetchall(self):
        return self.fetchall_return or []

    def __aiter__(self):
        self._iter = iter(self.iter_records)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration

class FakeRecord:
    """Record fittizio per a_get_tags_by_tag_names: deve avere attributi 'Name' e 'Description'."""
    def __init__(self, name, description, EnableCQA, EnableEnrichment, IdMonitoringQuestion):
        self.Name = name
        self.Description = description
        self.EnableCQA = EnableCQA
        self.EnableEnrichment = EnableEnrichment
        self.IdMonitoringQuestion = IdMonitoringQuestion

@pytest.mark.asyncio
async def test_rag_orchestrator_cqa_success(mocker, monkeypatch):
    set_mock_env(monkeypatch)
    logger = mocker.Mock(spec=Logger)
    mock_session = mocker.Mock()

    mock_cqa_do_query_result = CQAResponse(
        text_answer="L'assegno unico è...", cqa_data={"fake": "fake"})
    mocker.patch('logics.rag_orchestrator.cqa_do_query',
                 return_value=mock_cqa_do_query_result)

    # Simula le impostazioni MSSQL
    dummy_settings = SimpleNamespace(connection_string="dummy_connection_string")
    monkeypatch.setattr("services.mssql.get_mssql_settings", lambda: dummy_settings)

    # Prepara dei fake record da restituire tramite fetchall()
    fake_records = [
        FakeRecord("tag1", "desc1", True, True, 1),
        FakeRecord("tag2", "desc2", True, True, 1)
    ]
    fake_cursor = FakeCursor(fetchall_return=fake_records)
    # Sostituisce create_pool con il nostro fake (verrà usato nel context manager)
    monkeypatch.setattr("services.mssql.create_pool", lambda dsn, minsize: FakePoolContextManager(fake_cursor))

    # Importa e chiama la funzione da testare
    from services.mssql import a_get_tags_by_tag_names
    result = await a_get_tags_by_tag_names(logger, ["tag1", "tag2"])

    request = RagOrchestratorRequest(
        query="Cosa è l'assegno unico?", llm_model_id="OPENAI", tags=["auu"], environment="staging", configuration=RagConfiguration(enable_cqa=True, enable_enrichment=True))
    result = await logics.rag_orchestrator.a_get_query_response(request, logger, mock_session)

    assert isinstance(result, RagOrchestratorResponse)
    assert result.answer_text
    assert result.cqa_data
    assert result.llm_data == None


@pytest.mark.asyncio
async def test_get_query_response_cqa_fail_then_succeed(mocker, monkeypatch):
    set_mock_env(monkeypatch)
    logger = mocker.Mock(spec=Logger)
    mock_session = mocker.Mock()
    # Mock CQA
    test_rag_orchestrator_response = CQAResponse(
        text_answer="L'assegno unico è...", cqa_data={"fake": "fake"})
    mocker.patch('logics.rag_orchestrator.cqa_do_query',
                 side_effect=[None, test_rag_orchestrator_response])
    # Mock get prompt
    mock_prompt_info = [
        {
            "id": "51727AD5-1B91-4A4A-8B4B-C2E6B095F99F",
            "version": "1.0",
            "label": "enrichment"
        },
        {
            "id": "DECE6EC0-ED7A-40FC-9AAB-0E28A9E3C517",
            "version": "1.0",
            "label": "completion"
        },
        {
            "id": "2C4FD642-37BB-4660-9694-AFDE62C0BEB0",
            "version": "0.1",
            "label": "msd_intent_recognition"
        },
        {
            "id": "0CBDD307-4040-49FD-8CA1-CD1D0321C5E4",
            "version": "0.1",
            "label": "msd_completion"
        }
    ]
    mock_prompt_data = [PromptEditorResponseBody(version='1',
                                                 llm_model='OPENAI',
                                                 prompt=[],
                                                 parameters=[],
                                                 model_parameters=None,
                                                id = "guid",
                                                label = "tag",
                                                validation_messages=[]),
                        PromptEditorResponseBody(version='1',
                                                 llm_model='OPENAI',
                                                 prompt=[],
                                                 parameters=[],
                                                 model_parameters=None,
                                                 id = "guid",
                                                    label = "tag",
                                                    validation_messages=[]),
                        PromptEditorResponseBody(version='1',
                                                 llm_model='OPENAI',
                                                 prompt=[],
                                                 parameters=[],
                                                 model_parameters=None,
                                                 id = "guid",
                                                    label = "tag",
                                                    validation_messages=[]),
                        PromptEditorResponseBody(version='1',
                                                 llm_model='OPENAI',
                                                 prompt=[],
                                                 parameters=[],
                                                 model_parameters=None,
                                                 id = "guid",
                                                    label = "tag",
                                                    validation_messages=[])]
    mocker.patch('logics.rag_orchestrator.a_get_prompt_info', return_value=mock_prompt_info)
    mocker.patch('logics.rag_orchestrator.a_get_prompts_data', return_value=mock_prompt_data)
    mocker.patch('logics.rag_orchestrator.a_check_status_tag_for_mst', return_value=True)

    mock_language_service = mocker.Mock(spec=AiQueryServiceBase)
    mock_language_service.a_do_query_enrichment.return_value = mocker.Mock(standalone_question="Cos'è l'assegno unico?",
                                                                           end_conversation=False)
    mocker.patch('logics.ai_query_service_factory.AiQueryServiceFactory.get_instance',
                 return_value=mock_language_service)

    request = RagOrchestratorRequest(query="Aseno unco", llm_model_id="OPENAI", interactions=[
                                     {"question": "fake", "answer": "fake"}], tags=["auu"], environment="staging")

    # Simula le impostazioni MSSQL
    dummy_settings = SimpleNamespace(connection_string="dummy_connection_string")
    monkeypatch.setattr("services.mssql.get_mssql_settings", lambda: dummy_settings)

    # Prepara dei fake record da restituire tramite fetchall()
    fake_records = [
        FakeRecord("tag1", "desc1", True, True, 1),
        FakeRecord("tag2", "desc2", True, True, 1)
    ]
    fake_cursor = FakeCursor(fetchall_return=fake_records)
    # Sostituisce create_pool con il nostro fake (verrà usato nel context manager)
    monkeypatch.setattr("services.mssql.create_pool", lambda dsn, minsize: FakePoolContextManager(fake_cursor))

    # Importa e chiama la funzione da testare
    from services.mssql import a_get_tags_by_tag_names
    result = await a_get_tags_by_tag_names(logger, ["tag1", "tag2"])

    result = await logics.rag_orchestrator.a_get_query_response(request, logger, mock_session)

    assert isinstance(result, RagOrchestratorResponse)
    assert result.answer_text
    assert result.cqa_data
    assert result.llm_data == None
    mock_language_service.a_do_query_enrichment.assert_called_once_with(
        request, mock_prompt_data[0], logger)


@pytest.mark.asyncio
async def test_get_query_response_cqa_fail_twice_then_llm_succeed(mocker, monkeypatch):
    set_mock_env(monkeypatch)
    logger = mocker.Mock(spec=Logger)
    mock_session = mocker.Mock()
    # Mock CQA
    mocker.patch('logics.rag_orchestrator.cqa_do_query', return_value=None)
    # Mock get prompt
    
    mock_prompt_info = [
        {
            "id": "51727AD5-1B91-4A4A-8B4B-C2E6B095F99F",
            "version": "1.0",
            "label": "enrichment"
        },
        {
            "id": "DECE6EC0-ED7A-40FC-9AAB-0E28A9E3C517",
            "version": "1.0",
            "label": "completion"
        },
        {
            "id": "2C4FD642-37BB-4660-9694-AFDE62C0BEB0",
            "version": "0.1",
            "label": "msd_intent_recognition"
        },
        {
            "id": "0CBDD307-4040-49FD-8CA1-CD1D0321C5E4",
            "version": "0.1",
            "label": "msd_completion"
        }
    ]
    mock_prompt_data = [PromptEditorResponseBody(version='1',
                                                 llm_model='OPENAI',
                                                 prompt=[],
                                                 parameters=[],
                                                 model_parameters=None,
                                                 id = "guid",
                                                    label = "tag",
                                                    validation_messages=[]),
                        PromptEditorResponseBody(version='1',
                                                 llm_model='OPENAI',
                                                 prompt=[],
                                                 parameters=[],
                                                 model_parameters=None,
                                                 id = "guid",
                                                    label = "tag",
                                                    validation_messages=[]),
                        PromptEditorResponseBody(version='1',
                                                 llm_model='OPENAI',
                                                 prompt=[],
                                                 parameters=[],
                                                 model_parameters=None,
                                                 id = "guid",
                                                    label = "tag",
                                                    validation_messages=[]),
                        PromptEditorResponseBody(version='1',
                                                 llm_model='OPENAI',
                                                 prompt=[],
                                                 parameters=[],
                                                 model_parameters=None,
                                                 id = "guid",
                                                    label = "tag",
                                                    validation_messages=[])]
    mocker.patch('logics.rag_orchestrator.a_get_prompt_info', return_value=mock_prompt_info)
    mocker.patch('logics.rag_orchestrator.a_get_prompts_data', return_value=mock_prompt_data)
    mocker.patch('logics.rag_orchestrator.a_check_status_tag_for_mst', return_value=True)

    mock_language_service = mocker.Mock(spec=AiQueryServiceBase)
    mock_language_service.a_do_query_enrichment.return_value = mocker.Mock(standalone_question="Cos'è l'assegno unico?",
                                                                           end_conversation=False)
    mock_language_service.a_do_query.return_value = RagQueryResponse(
        "L'assegno unico è un ....", [], "stop", None, None, None, None, None)
    mocker.patch('logics.ai_query_service_factory.AiQueryServiceFactory.get_instance',
                 return_value=mock_language_service)

    request = RagOrchestratorRequest(query="Aseno unco", llm_model_id="OPENAI", interactions=[
                                     {"question": "fake", "answer": "fake"}], tags=["auu"], environment="staging")
    
    # Simula le impostazioni MSSQL
    dummy_settings = SimpleNamespace(connection_string="dummy_connection_string")
    monkeypatch.setattr("services.mssql.get_mssql_settings", lambda: dummy_settings)

    # Prepara dei fake record da restituire tramite fetchall()
    fake_records = [
        FakeRecord("tag1", "desc1", True, True, 1),
        FakeRecord("tag2", "desc2", True, True, 1)
    ]
    fake_cursor = FakeCursor(fetchall_return=fake_records)
    # Sostituisce create_pool con il nostro fake (verrà usato nel context manager)
    monkeypatch.setattr("services.mssql.create_pool", lambda dsn, minsize: FakePoolContextManager(fake_cursor))

    # Importa e chiama la funzione da testare
    from services.mssql import a_get_tags_by_tag_names
    result = await a_get_tags_by_tag_names(logger, ["tag1", "tag2"])
    
    result = await logics.rag_orchestrator.a_get_query_response(request, logger, mock_session)

    assert isinstance(result, RagOrchestratorResponse)
    assert result.answer_text
    assert result.cqa_data == None
    assert result.llm_data
    mock_language_service.a_do_query_enrichment.assert_called_once_with(
        request, mock_prompt_data[0], logger)


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


@pytest.mark.asyncio
async def test_intent_recognition_altro(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)
    logger = mocker.Mock(spec=Logger)
    mock_session = mocker.Mock()

    # Mock CQA to return None so we proceed to intent recognition
    mocker.patch('logics.rag_orchestrator.cqa_do_query', return_value=None)

    # Mock get prompt info
    mock_prompt_info = [
        {
            "id": "51727AD5-1B91-4A4A-8B4B-C2E6B095F99F",
            "version": "1.0",
            "label": "enrichment"
        },
        {
            "id": "DECE6EC0-ED7A-40FC-9AAB-0E28A9E3C517",
            "version": "1.0",
            "label": "completion"
        },
        {
            "id": "2C4FD642-37BB-4660-9694-AFDE62C0BEB0",
            "version": "0.1",
            "label": "msd_intent_recognition"
        },
        {
            "id": "0CBDD307-4040-49FD-8CA1-CD1D0321C5E4",
            "version": "0.1",
            "label": "msd_completion"
        }
    ]
    mock_prompt = PromptEditorResponseBody(version='1',
                                llm_model='OPENAI',
                                prompt=[],
                                parameters=[],
                                model_parameters=None,
                                id = "guid",
                                label = "tag",
                                validation_messages=[])

    mock_prompt_data = [mock_prompt, mock_prompt, mock_prompt, mock_prompt]
    
    mocker.patch('logics.rag_orchestrator.a_get_prompt_info', return_value=mock_prompt_info)
    mocker.patch('logics.rag_orchestrator.a_get_prompts_data', return_value=mock_prompt_data)
    
    # Mock check status tag to return False so we continue with intent recognition
    mocker.patch('logics.rag_orchestrator.a_check_status_tag_for_mst', return_value=False)

    # Mock enrichment response
    mock_enrichment_response = mocker.Mock(standalone_question="Test question", end_conversation=False)

    # Mock language service
    mock_language_service = mocker.Mock(spec=AiQueryServiceBase)
    mock_language_service.a_do_query_enrichment.return_value = mock_enrichment_response
    
    # Mock intent recognition to return "altro"
    mock_language_service.a_compute_classify_intent_query.return_value = mocker.Mock(intent="altro", stato_domanda=None)
    
    mocker.patch('logics.ai_query_service_factory.AiQueryServiceFactory.get_instance',
                 return_value=mock_language_service)

    # Create request
    request = RagOrchestratorRequest(
        query="Test query",
        llm_model_id="OPENAI",
        tags=["test_tag"],
        interactions=[{"question": "fake", "answer": "fake"}],
        environment="staging"
    )

    # Simula le impostazioni MSSQL
    dummy_settings = SimpleNamespace(connection_string="dummy_connection_string")
    monkeypatch.setattr("services.mssql.get_mssql_settings", lambda: dummy_settings)

    # Prepara dei fake record da restituire tramite fetchall()
    fake_records = [
        FakeRecord("tag1", "desc1", True, True, 2),
        FakeRecord("tag2", "desc2", True, True, 2)
    ]
    fake_cursor = FakeCursor(fetchall_return=fake_records)
    # Sostituisce create_pool con il nostro fake (verrà usato nel context manager)
    monkeypatch.setattr("services.mssql.create_pool", lambda dsn, minsize: FakePoolContextManager(fake_cursor))

    # Importa e chiama la funzione da testare
    from services.mssql import a_get_tags_by_tag_names
    result = await a_get_tags_by_tag_names(logger, ["tag1", "tag2"])

    # Act
    result = await logics.rag_orchestrator.a_get_query_response(request, logger, mock_session)

    # Assert
    assert mock_language_service.a_compute_classify_intent_query.called
    assert result is not None
    # Since intent is "altro", we should get a regular completion response
    assert mock_language_service.a_do_query.called
    
    
@pytest.mark.asyncio
async def test_intent_recognition_authenticated_user(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)
    logger = mocker.Mock(spec=Logger)
    mock_session = mocker.Mock()

    # Mock CQA to return None so we proceed to intent recognition
    mocker.patch('logics.rag_orchestrator.cqa_do_query', return_value=None)

    # Mock get prompt info
    mock_prompt_info = [
        {
            "id": "51727AD5-1B91-4A4A-8B4B-C2E6B095F99F",
            "version": "1.0",
            "label": "enrichment"
        },
        {
            "id": "DECE6EC0-ED7A-40FC-9AAB-0E28A9E3C517",
            "version": "1.0",
            "label": "completion"
        },
        {
            "id": "2C4FD642-37BB-4660-9694-AFDE62C0BEB0",
            "version": "0.1",
            "label": "msd_intent_recognition"
        },
        {
            "id": "0CBDD307-4040-49FD-8CA1-CD1D0321C5E4",
            "version": "0.1",
            "label": "msd_completion"
        }
    ]
    
    mock_prompt_data = [
        PromptEditorResponseBody(version='1',
                                llm_model='OPENAI',
                                prompt=[],
                                parameters=[],
                                model_parameters=None,
                                id = "guid",
                                label = "tag",
                                validation_messages=[]) for _ in range(4)
    ]
    
    mocker.patch('logics.rag_orchestrator.a_get_prompt_info', return_value=mock_prompt_info)
    mocker.patch('logics.rag_orchestrator.a_get_prompts_data', return_value=mock_prompt_data)
    mocker.patch('logics.rag_orchestrator.a_check_status_tag_for_mst', return_value=False)
    
    # Mock the blob storage with async support
    mock_blob_client = mocker.AsyncMock()  # Usa direttamente AsyncMock
    mock_blob_client.close = mocker.AsyncMock()  # Aggiungi questa linea!
    mock_downloader = mocker.AsyncMock()
    
    mock_blob_content = json.dumps([
        {"tag": "test_tag", "domus_form_application_code": "test_code", "domus_form_application_name": "test_name"}
    ]).encode("utf-8")  

    mock_downloader.readall = mocker.AsyncMock(return_value=mock_blob_content)
    
    mock_blob_client.download_blob = mocker.AsyncMock(return_value=mock_downloader)

    mock_blob_service = mocker.Mock()
    mock_blob_service.get_blob_client = mocker.Mock(return_value=mock_blob_client)

    mocker.patch('services.storage.get_blob_service_client', return_value=mock_blob_service)

    # Mock enrichment response
    mock_enrichment_response = mocker.Mock(standalone_question="Test question", end_conversation=False)

    # Mock language service with intent "verifica_stato"
    mock_language_service = mocker.Mock(spec=AiQueryServiceBase)
    mock_language_service.a_do_query_enrichment = mocker.AsyncMock(return_value=mock_enrichment_response)
    mock_language_service.a_compute_classify_intent_query = mocker.AsyncMock(
        return_value=mocker.Mock(
            intent="verifica_stato", 
            stato_domanda=["IN_CORSO"],
            numero_protocollo=["PROT123"],
            numero_domus=["PROT123"]
        )
    )
    
    # Mock domus service response
    mock_domus_response = mocker.Mock()
    mock_domus_response.errore = False
    mock_domus_response.messaggioErrore = ""
    mock_domus_response.listaDomande = [
        mocker.Mock(
            progressivoIstanza="1",
            numeroProtocollo="PROT123",
            numeroDomus="PROT123"
        )
    ]
    
    mocker.patch('services.domus.a_get_form_applications_by_fiscal_code', 
                 return_value=mock_domus_response)

    # Mock form application details
    mock_form_details = mocker.Mock()
    mock_form_details.errore = False
    mock_form_details.messaggioErrore = ""
    mock_form_details.model_dump = lambda: {"status": "IN_CORSO"}

    mocker.patch('services.domus.a_get_form_application_details',
                 return_value=mock_form_details)

    mocker.patch('logics.ai_query_service_factory.AiQueryServiceFactory.get_instance',
                 return_value=mock_language_service)

    # Mock domus answer
    mock_domus_answer = mocker.Mock(has_answer=True, answer="La tua domanda è in lavorazione")
    mock_language_service.a_get_domus_answer = mocker.AsyncMock(return_value=mock_domus_answer)

    # Create request with authenticated user
    request = RagOrchestratorRequest(
        query="A che punto è la mia domanda?",
        llm_model_id="OPENAI",
        tags=["test_tag"],
        user_fiscal_code="TESTFISCALCODE",
        token="test_token",
        environment="staging"
    )
    
    # Simula le impostazioni MSSQL
    dummy_settings = SimpleNamespace(connection_string="dummy_connection_string")
    monkeypatch.setattr("services.mssql.get_mssql_settings", lambda: dummy_settings)

    # Prepara dei fake record da restituire tramite fetchall()
    fake_records = [
        FakeRecord("tag1", "desc1", True, True, 2),
        FakeRecord("tag2", "desc2", True, True, 2)
    ]
    fake_cursor = FakeCursor(fetchall_return=fake_records)
    # Sostituisce create_pool con il nostro fake (verrà usato nel context manager)
    monkeypatch.setattr("services.mssql.create_pool", lambda dsn, minsize: FakePoolContextManager(fake_cursor))

    # Importa e chiama la funzione da testare
    from services.mssql import a_get_tags_by_tag_names
    result = await a_get_tags_by_tag_names(logger, ["tag1", "tag2"])

    # Act
    result = await logics.rag_orchestrator.a_get_query_response(request, logger, mock_session)

    # Assert
    assert result is not None
    assert isinstance(result, RagOrchestratorResponse)
    assert result.monitor_form_application is not None
    assert result.monitor_form_application.answer_text == "La tua domanda è in lavorazione"
    assert result.clog is not None
    assert result.clog.ret_code == 0

    # Verify service calls
    mock_language_service.a_compute_classify_intent_query.assert_called_once()
    mock_language_service.a_get_domus_answer.assert_called_once()
    
    
    
# Classe concreta per testare la classe astratta
class TestAiQueryService(AiQueryServiceBase):
    @staticmethod
    def model_id(cls):
        return "test-model"

    async def a_do_query(self, request, prompt_data, logger, session, domusData=None):
        return RagQueryResponse()
    
    async def a_do_query_enrichment(self, request, prompt_data, logger):
        return EnrichmentQueryResponse()

    async def a_compute_classify_intent_query(self, request, prompt_data, logger):
        return ClassifyIntentResponse()
    
    async def a_get_domus_answer(self, request, practice_detail, prompt_data, logger):
        return DomusAnswerResponse()

@pytest.mark.asyncio
async def test_get_topic_from_tags(mocker, monkeypatch):
    set_mock_env(monkeypatch)

    service = TestAiQueryService()
    logger = MagicMock(spec=Logger)
    mock_tags = [MagicMock(description="Tag1"), MagicMock(description="Tag2")]
    
    # Mock di a_get_tags_by_tag_names
    mocker.patch("logics.ai_query_service_base.a_get_tags_by_tag_names", new=AsyncMock(return_value=mock_tags))
    
    topic = await service.get_topic_from_tags(logger, ["Tag1", "Tag2"])
    assert topic == "Tag1,Tag2"

@pytest.mark.asyncio
async def test_get_topic_from_tags_empty(mocker, monkeypatch):
    set_mock_env(monkeypatch)
    service = TestAiQueryService()
    logger = MagicMock(spec=Logger)
    mocker.patch("logics.ai_query_service_base.a_get_tags_by_tag_names", new=AsyncMock(return_value=[]))
    
    topic = await service.get_topic_from_tags(logger, ["Tag1", "Tag2"])
    assert topic == ""

@pytest.mark.asyncio
async def test_extract_chat_history(monkeypatch):
    set_mock_env(monkeypatch)
    service = TestAiQueryService()
    interactions = [
        Interaction(question="Hello?", answer="Hi!"),
        Interaction(question="How are you?", answer="Good, thanks!"),
    ]
    result = service.extract_chat_history(interactions)
    
    expected_result = os.linesep.join([
    "user: Hello?",
    "assistant: Hi!",
    "user: How are you?",
    "assistant: Good, thanks!"
    ])
    
    assert result == expected_result

@pytest.mark.asyncio
async def test_extract_chat_history_empty(monkeypatch):
    set_mock_env(monkeypatch)
    service = TestAiQueryService()
    result = service.extract_chat_history([])
    assert result == ""
