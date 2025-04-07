
import pytest
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from constants import llm
from models.apis.prompt_editor_response_body import PromptEditorResponseBody, OpenAIModelParameters
from models.apis.prompt_template_response_body import TemplateResolveResponse
from models.services.llm_context_document import LlmContextContent
from services.openai import (
    a_get_answer_from_context as openai_get_answer_from_context,
    a_get_answer_from_domus,
    a_get_enriched_query as openai_get_enriched_query,
    a_get_intent_from_enriched_query,
    a_resolve_template,
    check_prompt_variables
    )
from tests.mock_env import set_mock_env
from tests.mock_logging import MockLogger

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
    mock_model_parameters = OpenAIModelParameters(0.0, 0.8, 2000, None)
    mock_prompt_data = PromptEditorResponseBody(version = '1',
                                                    llm_model=llm.openai,
                                                    prompt = [],
                                                    parameters=[],
                                                    model_parameters= mock_model_parameters,
                                                    id = "guid",
                                                    label = "tag",
                                                    validation_messages=[])
    # Sample question and context
    question = "What is the capital of France?"
    interactions = []
    lang = "en"
    #mock_context = {
     #   "chunk_id":"id"} 
    context = [LlmContextContent("id", 1, 5.0)]                   
    #"mock_context.chunk_id = "id"
    #mock_context.toJSON.return_value = "json str"
    #context = [mock_context]

   # mocker.patch(
   #     "services.openai.asdict"
   # )

    mocker.patch(
        "services.openai.check_prompt_variables",
        return_value=[0]
    )

    mock_chat_prompt_template.from_messages.return_value = "Mocked Prompt"
    mock_azure_chat_openai.complete.return_value = True
    mock_parser_result = mocker.Mock()

    mock_parser = mocker.patch.object(PydanticOutputParser, "ainvoke")
    mock_parser.response = "Paris"
    mock_parser.return_value = mock_parser
    # Act
    result = await openai_get_answer_from_context(question, lang,
                                            context,
                                            mock_prompt_data,
                                            mock_logger,
                                            interactions)

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
    mock_model_parameters = OpenAIModelParameters(0.0, 0.8, 2000, None)
    mock_prompt_data = PromptEditorResponseBody(version = '1',
                                                    llm_model='OPENAI',
                                                    prompt = [],
                                                    parameters=[],
                                                    model_parameters= mock_model_parameters,
                                                    id = "guid",
                                                    label = "tag",
                                                    validation_messages=[])
    
    mocker.patch(
        "services.openai.check_prompt_variables",
        return_value=[0]
    )

    mock_chat_prompt_template.from_messages.return_value = "Mocked Prompt"
    mock_azure_chat_openai.complete.return_value = True
    mock_azure_chat_openai.content =  '{\n\t"standalone_question": "Quali sono i requisiti per accedere all\'Assegno Unico Universale?",\n    "end_conversation": false\n}'

    mock_parser_value = mocker.Mock()
    mock_parser_value.standalone_question = "standalone question"
    mock_parser_value.end_conversation = False
    mock_parser = mocker.patch.object(PydanticOutputParser, "ainvoke")
    mock_parser.return_value = mock_parser_value
    # Act
    result = await openai_get_enriched_query("testo di prova", ["auu"], "", mock_prompt_data, mock_logger)

    # Assert
    assert result.standalone_question == "standalone question"

@pytest.mark.asyncio 
async def test_get_intent_from_enriched_query(mocker,
                             monkeypatch,
                             mock_chat_prompt_template,
                             mock_azure_chat_openai):
        # Arrange
    set_mock_env(monkeypatch)
    mock_logger = MockLogger()
    mock_model_parameters = OpenAIModelParameters(0.0, 0.8, 2000, None)
    mock_prompt_data = PromptEditorResponseBody(version = '1',
                                                    llm_model='OPENAI',
                                                    prompt = [],
                                                    parameters=[],
                                                    model_parameters= mock_model_parameters,
                                                    id = "guid",
                                                    label = "tag",
                                                    validation_messages=[])
    # Sample question and context
    question = "Quale è lo stato della mia pratica"

    mocker.patch(
        "services.openai.check_prompt_variables",
        return_value=[0]
    )

    mock_chat_prompt_template.from_messages.return_value = "Mocked Prompt"
    mock_azure_chat_openai.complete.return_value = True

    mock_parser = mocker.patch.object(PydanticOutputParser, "ainvoke")
    mock_parser.intent = "Lista"
    mock_parser.return_value = mock_parser
    # Act
    result = await a_get_intent_from_enriched_query(question,                       
                                            mock_prompt_data,
                                            mock_logger)

    # Assert
    assert result.intent == "Lista"

@pytest.mark.asyncio 
async def test_get_answer_from_domus(mocker,
                             monkeypatch,
                             mock_chat_prompt_template,
                             mock_azure_chat_openai):
    # Arrange
    set_mock_env(monkeypatch)
    mock_logger = MockLogger()
    mock_model_parameters = OpenAIModelParameters(0.0, 0.8, 2000, None)
    mock_prompt_data = PromptEditorResponseBody(version = '1',
                                                    llm_model='OPENAI',
                                                    prompt = [],
                                                    parameters=[],
                                                    model_parameters= mock_model_parameters,
                                                    id = "guid",
                                                    label = "tag",
                                                    validation_messages=[])
    # Sample question and context
    question = "Quale è lo stato della mia pratica"
    practice_detail = "json practice detail"

    mocker.patch(
        "services.openai.check_prompt_variables",
        return_value=[0]
    )

    mock_chat_prompt_template.from_messages.return_value = "Mocked Prompt"
    mock_azure_chat_openai.complete.return_value = True

    mock_parser = mocker.patch.object(PydanticOutputParser, "ainvoke")
    mock_parser.answer = "Sospesa"
    mock_parser.return_value = mock_parser
    # Act
    result = await a_get_answer_from_domus(question,
                                            practice_detail,
                                            mock_prompt_data,
                                            mock_logger)

    # Assert
    assert result.answer == "Sospesa"

@pytest.mark.asyncio 
async def test_a_resolve_template(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)
    mock_logger = MockLogger()
    mock_model_parameters = OpenAIModelParameters(0.0, 0.8, 2000, None)
    mock_template_data = {}
    mock_prompt_data = PromptEditorResponseBody(version = '1',
                                                    llm_model='OPENAI',
                                                    prompt = [],
                                                    parameters=[],
                                                    model_parameters= mock_model_parameters,
                                                    id = "guid",
                                                    label = "tag",
                                                    validation_messages=[])
    mock_resolve_template = TemplateResolveResponse(resolved_template="text resolved",
                                                    parameters=[],
                                                    validation_messages=[]) 
    mocker.patch(
        "services.openai.a_get_prompt_from_resolve_jinja_template_api",
        return_value=mock_resolve_template
    )
    # Act
    result = await a_resolve_template(mock_logger,
                                    mock_prompt_data,
                                    mock_template_data)

    # Assert
    assert result.llm_model == "OPENAI"

def test_check_prompt_variables(mocker):
    #Arrange
    mock_model_parameters = OpenAIModelParameters(0.0, 0.8, 2000, None)
    mock_prompt_data = PromptEditorResponseBody(version = '1',
                                                    llm_model='OPENAI',
                                                    prompt = [],
                                                    parameters=["topic", "chat"],
                                                    model_parameters= mock_model_parameters,
                                                    id = "guid",
                                                    label = "tag",
                                                    validation_messages=[])
    fixed_params= ["question", "topic"]

    # Act
    result = check_prompt_variables(mock_prompt_data, fixed_params)

    #Assert
    assert len(result) == 1