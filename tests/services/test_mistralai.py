from langchain_core.prompts import ChatPromptTemplate
from langchain_mistralai import ChatMistralAI
from langchain_core.output_parsers.pydantic import PydanticOutputParser
import pytest

from exceptions.custom_exceptions import CustomPromptParameterError
from constants import llm
from models.apis.prompt_editor_response_body import OpenAIModelParameters, PromptEditorResponseBody
from services.openai import check_prompt_variables
from tests.mock_env import set_mock_env
from tests.mock_logging import MockLogger
from services.mistralai import (a_get_answer_from_context as mistralai_get_answer_from_context, 
                                a_get_enriched_query as mistralai_get_enriched_query,
                                a_get_answer_from_domus, a_get_intent_from_enriched_query
                                )
from models.services.llm_context_document import LlmContextContent

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


@pytest.fixture
def a_get_answer_from_domus_mistralai(mocker):
    mock = mocker.patch.object(ChatMistralAI, "ainvoke")
    mock_message = mocker.Mock()
    mock_message.content = '{"reason": "It is ok", "answer": "this is my answer", "has_answer": true }'
    mock_message.json.return_value = '{"reason": "It is ok", "answer": "this is my answer", "has_answer": "true" }'
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
    lang = "en"
    mock_context = mocker.Mock()
    mock_context.chunk_id = "id"
    mock_context.toJSON.return_value = "json str"
    context = [mock_context]
    mock_model_parameters = OpenAIModelParameters(0.0, 0.8, 2000, None)
    mock_prompt_data = PromptEditorResponseBody(version = '1',
                                                    llm_model=llm.mistralai,
                                                    prompt = [],
                                                    parameters=[],
                                                    model_parameters= mock_model_parameters,
                                                    id = "guid",
                                                    label = "tag",
                                                    validation_messages=[]) 
    # Sample question and context
    question = "What is the capital of France?"
    lang = "en"
    mock_context = mocker.Mock()
    mock_context.chunk_id = "id"
    mock_context.toJSON.return_value = "json str"
    context = [mock_context]

    mocker.patch(
        "services.mistralai.asdict"
    )

    mocker.patch(
        "services.mistralai.check_prompt_variables",
        return_value=[0]
    )

    mock_chat_prompt_template.from_messages.return_value = "Mocked Prompt"
    mock_azure_chat_mistralai.complete.return_value = True
    mock_parser_result = mocker.Mock()

    mock_parser = mocker.patch.object(PydanticOutputParser, "ainvoke")
    mock_parser.response = "Paris"
    mock_parser.return_value = mock_parser
    # Act
    result = await mistralai_get_answer_from_context(question, lang,
                                            context,
                                            mock_prompt_data,
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
        "services.mistralai.check_prompt_variable",
        return_value=True
    )   
    mock_chat_prompt_template.from_messages.return_value = "Mocked Prompt"
    mock_azure_chat_mistralai.complete.return_value = True
    mock_azure_chat_mistralai.content =  '{\n\t"standalone_question": "standalone question",\n    "end_conversation": false\n}'

    mock_parser_value = mocker.Mock()
    mock_parser_value.standalone_question = "standalone question"
    mock_parser_value.end_conversation = False
    mock_parser = mocker.patch.object(PydanticOutputParser, "ainvoke")
    mock_parser.return_value = mock_parser_value
    
    # Act
    result = await mistralai_get_enriched_query("testo di prova", ["auu"], "", mock_prompt_data, mock_logger)

    # Assert
    assert result.standalone_question == "standalone question"

@pytest.mark.asyncio 
async def test_get_intent_from_enriched_query(mocker,
                             monkeypatch,
                             mock_chat_prompt_template,
                             mock_azure_chat_mistralai):
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
        "services.mistralai.check_prompt_variable",
        return_value=True
    )

    mock_chat_prompt_template.from_messages.return_value = "Mocked Prompt"
    mock_azure_chat_mistralai.complete.return_value = True
    mock_azure_chat_mistralai.content = ""

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
                             mock_azure_chat_mistralai):
    # Arrange
    set_mock_env(monkeypatch)
    mock_logger = MockLogger()
    mock_model_parameters = OpenAIModelParameters(0.0, 0.8, 2000, None)
    mock_prompt_data = PromptEditorResponseBody(version = '1',
                                                    llm_model='MISTRAL',
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
    mock_azure_chat_mistralai.complete.return_value = True

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
async def test_get_intent_from_enriched_query_custom_error(mocker,
                             monkeypatch,
                             mock_chat_prompt_template,
                             mock_azure_chat_mistralai):
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
        "services.mistralai.check_prompt_variable",
        return_value=False
    )
    
    # Act
    with pytest.raises(CustomPromptParameterError) as excinfo:
        result = await a_get_intent_from_enriched_query(question,                       
                                            mock_prompt_data,
                                            mock_logger)



def test_check_prompt_variables(mocker):
    #Arrange
    mock_model_parameters = OpenAIModelParameters(0.0, 0.8, 2000, None)
    mock_prompt_data = PromptEditorResponseBody(version = '1',
                                                    llm_model='MISTRAL',
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

# @pytest.mark.asyncio
# async def test_get_answer_from_domus_custom_error(mocker,
#                                 monkeypatch,
#                                 mock_chat_prompt_template,
#                                 a_get_answer_from_domus_mistralai):
#         # Arrange
#     set_mock_env(monkeypatch)
#     mock_logger = MockLogger()
#     mock_model_parameters = OpenAIModelParameters(0.0, 0.8, 2000, None)
#     mock_prompt_data = PromptEditorResponseBody(version = '1',
#                                                     llm_model='OPENAI',
#                                                     prompt = [],
#                                                     parameters=[],
#                                                     model_parameters= mock_model_parameters,
#                                                     id = "guid",
#                                                     label = "tag",
#                                                     validation_messages=[])
#     # Sample question and context
#     question = "Quale è lo stato della mia pratica"
#     practice_detail = "json practice detail"

#     mocker.patch(
#         "services.mistralai.check_prompt_variable",
#         return_value=False
#     )

#     # Act
#     with pytest.raises(CustomPromptParameterError) as excinfo:
#         result = await a_get_answer_from_domus(question,
#                                             practice_detail,
#                                             mock_prompt_data,
#                                             mock_logger)

