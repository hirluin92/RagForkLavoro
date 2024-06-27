
import pytest
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from services.openai import (
    a_get_answer_from_context as openai_get_answer_from_context,
    a_get_enriched_query as openai_get_enriched_query
    )
from tests.mock_logging import MockLogger

def set_mock_env(monkeypatch):
    monkeypatch.setenv('AZURE_OPENAI_API_VERSION', 'version')
    monkeypatch.setenv('AZURE_OPENAI_COMPLETION_ENDPOINT', 'endpoint')
    monkeypatch.setenv('AZURE_OPENAI_COMPLETION_KEY', 'key')
    monkeypatch.setenv('AZURE_OPENAI_COMPLETION_TOKENS', "2000")
    monkeypatch.setenv('AZURE_OPENAI_COMPLETION_TEMPERATURE', "0")
    monkeypatch.setenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT_MODEL', 'model')
    monkeypatch.setenv('AZURE_OPENAI_EMBEDDING_ENDPOINT', 'endpoint')
    monkeypatch.setenv('AZURE_OPENAI_EMBEDDING_KEY', 'kery')
    monkeypatch.setenv('AZURE_OPENAI_COMPLETION_DEPLOYMENT_MODEL', 'model')
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
def mock_azure_chat_openai(mocker):
    mock = mocker.patch.object(AzureChatOpenAI, "ainvoke")
    mock_message = mocker.Mock()
    mock_message.content = '{"response": "Paris", "standalone_question": "standalone question", "end_conversation": false }'
    mock_message.json.return_value = '{"response": "Paris", "standalone_question": "standalone question", "end_conversation": false }'
    mock.return_value = mock_message
    return mock

@pytest.mark.asyncio
async def test_openai_get_answer_from_context(mocker,
                                        monkeypatch,
                                        mock_chat_prompt_template,
                                        mock_azure_chat_openai):
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
    mock_azure_chat_openai.complete.return_value = True
    mock_parser_result = mocker.Mock()

    mock_parser = mocker.patch.object(PydanticOutputParser, "ainvoke")
    mock_parser.response = "Paris"
    mock_parser.return_value = mock_parser
    # Act
    result = await openai_get_answer_from_context(question,
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
                             mock_azure_chat_openai):
    # Arrange
    set_mock_env(monkeypatch)
    mock_logger = MockLogger()
    
    mocker.patch('services.openai.a_get_blob_content_from_container', side_effect=["prima", "seconda", '{"auu": "Assegno unico universale", "supportoformazionelavoro": "Supporto Formazione Lavoro"}'])
    mock_chat_prompt_template.from_messages.return_value = "Mocked Prompt"
    mock_azure_chat_openai.complete.return_value = True
    mock_azure_chat_openai.content =  '{\n\t"standalone_question": "Quali sono i requisiti per accedere all\'Assegno Unico Universale?",\n    "end_conversation": false\n}'

    mock_parser_value = mocker.Mock()
    mock_parser_value.standalone_question = "standalone question"
    mock_parser_value.end_conversation = False
    mock_parser = mocker.patch.object(PydanticOutputParser, "ainvoke")
    mock_parser.return_value = mock_parser_value
    # Act
    result = await openai_get_enriched_query("testo di prova", ["auu"], "", mock_logger)

    # Assert
    assert result.standalone_question == "standalone question"

    
    