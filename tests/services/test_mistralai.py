from langchain_core.prompts import ChatPromptTemplate
from langchain_mistralai import ChatMistralAI
from langchain_core.output_parsers.pydantic import PydanticOutputParser
import pytest

from tests.mock_logging import MockLogger
from services.mistralai import (a_get_answer_from_context as mistralai_get_answer_from_context, 
                                a_get_enriched_query as mistralai_get_enriched_query
                                )


def set_mock_env(monkeypatch):
    monkeypatch.setenv('AZURE_MISTRALAI_ENDPOINT', 'endpoint')
    monkeypatch.setenv('AZURE_MISTRALAI_KEY', 'key')
    monkeypatch.setenv('AZURE_MISTRALAI_MODEL', 'model')
    monkeypatch.setenv('AZURE_MISTRALAI_TEMPERATURE', '0')
    monkeypatch.setenv('AZURE_MISTRALAI_TOKENS', '2000')
    monkeypatch.setenv('STORAGE_BULK_SPLIT_FILES_CONTAINER', 'container')
    monkeypatch.setenv('STORAGE_DATA_SOURCE_SPLIT_FILES_CONTAINER', 'container')
    monkeypatch.setenv('STORAGE_CONNECTION_STRING', 'connection_string')
    monkeypatch.setenv('STORAGE_PROMPT_FILES_CONTAINER', 'container')
    monkeypatch.setenv('STORAGE_UPLOADED_FILES_CONTAINER', 'container')
    monkeypatch.setenv('STORAGE_UPLOADED_SPLIT_FILES_CONTAINER', 'container')

@pytest.fixture
def mock_chat_prompt_template(mocker):
    return mocker.Mock(spec=ChatPromptTemplate)


@pytest.fixture
def mock_azure_chat_mistralai(mocker):
    mock = mocker.patch.object(ChatMistralAI, "ainvoke")
    mock_message = mocker.Mock()
    mock_message.content = '{"response": "Paris", "standalone_question": "standalone question", "end_conversation": false }'
    mock_message.json.return_value = '{"response": "Paris", "standalone_question": "standalone question", "end_conversation": false }'
    mock.return_value = mock_message
    return mock

@pytest.mark.asyncio
async def test_mistralai_get_answer_from_context(mocker,
                                           monkeypatch,
                                           mock_chat_prompt_template,
                                           mock_azure_chat_mistralai):
    # Arrange
    set_mock_env(monkeypatch)
    mock_logger = MockLogger()

    # Sample question and context
    question = "What is the capital of France?"
    mock_context = mocker.Mock()
    mock_context.chunk_id = "id"
    mock_context.toJSON.return_value = "json str"
    context = [mock_context]

    mock_chat_prompt_template.from_messages.return_value = "Mocked Prompt"
    mock_azure_chat_mistralai.complete.return_value = True
    mock_parser = mocker.patch.object(PydanticOutputParser, "ainvoke")
    mock_parser.response = "Paris"
    mock_parser.return_value = mock_parser

    # Act
    result = await mistralai_get_answer_from_context(question,
                                               context,
                                               "SYSTEM_PROMPT",
                                               "USER_PROMPT",
                                               mock_logger)

    # Assert
    assert result.response == "Paris"

@pytest.mark.asyncio
async def test_do_query_enrichment(mocker,
                             monkeypatch,
                             mock_chat_prompt_template,
                             mock_azure_chat_mistralai):
    # Arrange
    set_mock_env(monkeypatch)
    mock_logger = MockLogger()
    
    mocker.patch('services.mistralai.a_get_blob_content_from_container', side_effect=["prima", "seconda", '{"auu": "Assegno unico universale", "supportoformazionelavoro": "Supporto Formazione Lavoro"}'])
    mock_chat_prompt_template.from_messages.return_value = "Mocked Prompt"
    mock_azure_chat_mistralai.complete.return_value = True
    mock_azure_chat_mistralai.content =  '{\n\t"standalone_question": "standalone question",\n    "end_conversation": false\n}'

    mock_parser_value = mocker.Mock()
    mock_parser_value.standalone_question = "standalone question"
    mock_parser_value.end_conversation = False
    mock_parser = mocker.patch.object(PydanticOutputParser, "ainvoke")
    mock_parser.return_value = mock_parser_value
    
    # Act
    result = await mistralai_get_enriched_query("testo di prova", ["auu"], "", mock_logger)

    # Assert
    assert result.standalone_question == "standalone question"

    