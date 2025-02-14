import pytest
from unittest.mock import AsyncMock, MagicMock
import json
from aiohttp import ClientSession, ClientResponse
from services.prompt_editor import a_get_prompts_data
from services.prompt_editor import a_get_response_from_prompt_retrieval_api, PromptEditorResponseBody
from services.logging import Logger
from tests.mock_env import set_mock_env

@pytest.mark.asyncio
async def test_a_get_response_from_prompt_retrieval_api(monkeypatch):
    # Mock dei settings per evitare l'accesso a variabili di ambiente reali
    set_mock_env(monkeypatch)
    
    mock_settings = MagicMock()
    mock_settings.editor_endpoint = "https://mocked.endpoint"
    mock_settings.editor_api_key = "mocked_api_key"
    
    # Mock del ClientSession
    mock_session = AsyncMock(spec=ClientSession)
    
    # Mock della risposta HTTP con struttura corretta
    mock_response = AsyncMock(spec=ClientResponse)
    mock_response.json = AsyncMock(return_value={
        "version": "1.0",
        "llm_model": "model_name",
        "prompt": [{"role": "user", "content": "Hello"}],
        "parameters": ["param1", "param2"],
        "model_parameters": {
            "top_p": 0.9,
            "temperature": 0.7,
            "max_length": 100,
            "stop_sequence": "END"
        },
        "label": "example"
    })
    
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    # Mock del logger
    mock_logger = MagicMock(spec=Logger)
    mock_logger.track_event = MagicMock()   
    
    # test
    prompt_id = "1234"
    response = await a_get_response_from_prompt_retrieval_api(prompt_id, mock_logger, mock_session)

    # Verifica che la risposta sia corretta
    assert isinstance(response, PromptEditorResponseBody)
    assert response.llm_model == "model_name"  # Verifica se l'oggetto è costruito correttamente
    assert response.model_parameters.top_p == 0.9  # Verifica se model_parameters è correttamente mappato

@pytest.mark.asyncio
async def test_a_get_prompts_data(monkeypatch):
    set_mock_env(monkeypatch)
    #  mock credenziali per prompt type
    mock_prompt_editor = [
        MagicMock(type="msd_intent_recognition", id="123", version="v1", label="msd_intent_recognition"),
        MagicMock(type="enrichment", id="789", version="v3", label="enrichment"),
        MagicMock(type="msd_completion", id="999", version="v4", label="msd_completion")
    ]
    mock_list_prompt_version_info = [
        MagicMock(type="completion", id="456", version="v2", label="completion")
    ]
    
    # Mock del ClientSession
    mock_session = AsyncMock(spec=ClientSession)
    
    # risposta HTTP dummy con 4 elementi, uno per ciascun prompt type atteso
    dummy_response_list = [
        {
            "version": "dummy",
            "llm_model": "dummy",
            "prompt": [],
            "parameters": [],
            "model_parameters": {"top_p": 1.0, "temperature": 0.5, "max_length": 100, "stop_sequence": None},
            "label": "enrichment"
        },
        {
            "version": "dummy",
            "llm_model": "dummy",
            "prompt": [],
            "parameters": [],
            "model_parameters": {"top_p": 1.0, "temperature": 0.5, "max_length": 100, "stop_sequence": None},
            "label": "completion"
        },
        {
            "version": "dummy",
            "llm_model": "dummy",
            "prompt": [],
            "parameters": [],
            "model_parameters": {"top_p": 1.0, "temperature": 0.5, "max_length": 100, "stop_sequence": None},
            "label": "msd_intent_recognition"
        },
        {
            "version": "dummy",
            "llm_model": "dummy",
            "prompt": [],
            "parameters": [],
            "model_parameters": {"top_p": 1.0, "temperature": 0.5, "max_length": 100, "stop_sequence": None},
            "label": "msd_completion"
        }
    ]
    
    # Mock della risposta HTTP
    mock_response = AsyncMock(spec=ClientResponse)
    mock_response.json = AsyncMock(return_value=dummy_response_list)
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    # Mock del logger
    mock_logger = MagicMock(spec=Logger)
    
    # test
    response = await a_get_prompts_data(mock_prompt_editor, mock_list_prompt_version_info, mock_logger, mock_session)
    
    # La funzione dovrebbe restituire una tupla con 4 PromptEditorResponseBody
    assert isinstance(response, tuple)
    assert len(response) == 4
    
    enrichment_response, completion_response, msd_intent_response, msd_completion_response = response
    
    # Verifica che le etichette (label) corrispondano
    assert enrichment_response.label == "enrichment"
    assert completion_response.label == "completion"
    assert msd_intent_response.label == "msd_intent_recognition"
    assert msd_completion_response.label == "msd_completion"