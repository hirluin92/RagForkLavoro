import pytest
import json
from unittest.mock import AsyncMock, Mock
from aiohttp import ClientSession, ClientResponse
from logics.rag_orchestrator import check_msd_question
from models.apis.rag_orchestrator_request import RagOrchestratorRequest
from models.apis.rag_orchestrator_response import RagOrchestratorResponse
from models.configurations.llm_consumer import LLMConsumer
from services.domus import a_get_form_applications_by_fiscal_code, a_get_form_application_details
from models.apis.domus_form_applications_by_fiscal_code_request import DomusFormApplicationsByFiscalCodeRequest
from models.apis.domus_form_applications_by_fiscal_code_response import DomusFormApplicationsByFiscalCodeResponse
from models.apis.domus_form_application_details_request import DomusFormApplicationDetailsRequest
from models.apis.domus_form_application_details_response import DomusFormApplicationDetailsResponse
from models.configurations.domus import DomusApiSettings
from tests.mock_env import set_mock_env
from tests.mock_logging import set_mock_logger_builder

@pytest.mark.asyncio
async def test_a_get_form_applications_by_fiscal_code(mocker, monkeypatch):
    # Arrange: Mock delle variabili d'ambiente
    set_mock_env(monkeypatch)

    request = DomusFormApplicationsByFiscalCodeRequest(
        user_fiscal_code="ABC123XYZ",
        language="IT",
        token="test_token",
        form_application_code="12345"
    )

    mock_logger = mocker.Mock()
    mock_session = AsyncMock(spec=ClientSession)

    # Mock della risposta HTTP
    mock_response = AsyncMock(spec=ClientResponse)
    mock_response.json = AsyncMock(return_value={
        "messaggioErrore": None,
        "errore": None,
        "numeroPagine": 1,
        "numeroTotaleElementi": 1,
        "listaDomande": [
            {
                "codiceProceduraDomus": "12345",
                "numeroDomus": "D001",
                "progressivoIstanza": "001",
                "nomePrestazione": "Prestazione Test",
                "dataPresentazione": "2024-02-14T12:00:00Z",
                "numeroProtocollo": "PR12345",
                "statoDomanda": {
                    "dataAggiornamento": "2024-02-14T12:00:00Z",  
                    "stato": "APPROVATA",  
                    "sottostato": "Sottostato Esempio"  
                },
                "sede": "Sede Test",
                "modalitaVisualizzazione": "ONLINE",
                "codiceProdottoDomus": "P001",
                "codiceStatoDomandaDomus": "ST001",
                "dettagliDomanda": "Dettaglio Test"
            }
        ]
    })


    mock_session.post.return_value.__aenter__.return_value = mock_response

    # Act
    response = await a_get_form_applications_by_fiscal_code(request, mock_session, mock_logger)

    # Assert
    assert isinstance(response, DomusFormApplicationsByFiscalCodeResponse)
    mock_logger.track_event.assert_called()



@pytest.mark.asyncio
async def test_a_get_form_application_details(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)
    set_mock_logger_builder(mocker)
    
    request = DomusFormApplicationDetailsRequest(
        domus_number="123456",
        language="IT",
        progressivo_istanza="789",
        token="test_token"
    )
    
    mock_logger = mocker.Mock()
    mock_session = AsyncMock(spec=ClientSession)
    
    # Mock della risposta HTTP con tutti i campi obbligatori
    mock_response = AsyncMock(spec=ClientResponse)
    mock_response.json = AsyncMock(return_value={
        "prodotto": "some_product",  # Optional
        "nomeCompleto": "John Doe",  # Optional
        "dataPresentazione": 20250101,  # Optional
        "numeroDomus": "123456",  # Optional
        "progressivoIstanza": 789,  # Optional
        "numeroProtocollo": "protocol_number",  # Optional
        "siglaPatronato": "patronage_code",  # Required
        "modalitaPresentazione": "online",  # Required
        "listaStati": [],  # Required
        "adempimenti": [],  # Required
        "codiceFiscaleTitolareDomanda": "ABCDEF12G34H567I",  # Required
        "scopeStatoCorrente": "current_scope",  # Required
        "codiceProdottoDomus": "product_code",  # Required
        "codiceProceduraDomus": 1,  # Required
        "codiceStatoDomandaDomus": "state_code",  # Required
        "listaDocumentiDomanda": [],  # Required
        "codiceProdotto": "product_code",  # Required
        "codiceSottoprodotto": "subproduct_code",  # Required
        "errore": False,  # Required
        "messaggioErrore": "",  # Required
        "codiceErrore": ""  # Required
    })
    
    
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    # Act
    response = await a_get_form_application_details(request, mock_session, mock_logger)
    
    # Assert
    assert isinstance(response, DomusFormApplicationDetailsResponse)
    mock_logger.track_event.assert_called()




@pytest.mark.asyncio
async def test_check_msd_question_no_domus_no_protocollo(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)
    set_mock_logger_builder(mocker)

    request = RagOrchestratorRequest(
        conversation_id="convid_001",
        user_fiscal_code="ABCDEF12G34H567I",
        token="fake-token",
        query="qual è lo stato delle mie domande",
        llm_model_id="OPENAI",
        model_name="INPS_gpt4o"
    )

    # intent_result con nessun numero_domus e numero_protocollo
    intent_result_mock = mocker.Mock()
    intent_result_mock.intent = "domus"
    intent_result_mock.numero_domus = None
    intent_result_mock.numero_protocollo = None

    # mock del servizio language
    language_service = mocker.Mock()
    language_service.a_compute_classify_intent_query = AsyncMock(return_value=intent_result_mock)

    # mock redisService
  
    mock_payload = {
    "messaggioErrore": None,
    "errore": False,
    "numeroPagine": 1,
    "numeroTotaleElementi": 2,
    "listaDomande": [
        {
            "numeroDomus": "XXXXXXX",
            "progressivoIstanza": 1,
            "nomePrestazione": "XXXXXXXX",
            "dataPresentazione": "26/10/2022",
            "numeroProtocollo": "XXXXX",
            "statoDomanda": {
                "dataAggiornamento": "",
                "stato": "IN LAVORAZIONE",
                "sottostato": ""
            },
            "sede": "NARDO",
            "modalitaVisualizzazione": "ConContenuti",
            "codiceProdottoDomus": "040909",
            "codiceProceduraDomus": 9,
            "codiceStatoDomandaDomus": "",
            "dettagliDomanda": "XXXX"          
        },
        {
            "numeroDomus": "XXXX",
            "progressivoIstanza": 1,
            "nomePrestazione": "XXXXXXXXX",
            "dataPresentazione": "13/01/2020",
            "numeroProtocollo": "IXXXXXXX",
            "statoDomanda": {
                "dataAggiornamento": "",
                "stato": "",
                "sottostato": ""
            },
            "sede": "XXXXXXX",
            "modalitaVisualizzazione": "ConContenuti",
            "codiceProdottoDomus": "040909",
            "codiceProceduraDomus": 9,
            "codiceStatoDomandaDomus": "RESP",
            "dettagliDomanda": "XXXXX"
        }
    ],
    "clog": None
}

# patch del metodo Redis nel test
    mock_redis = mocker.patch(
        "services.redis.get_from_redis",
        return_value=json.dumps(mock_payload)   #  JSON ben formato
        )


     
    mock_redis.make_key.return_value = "list_convid_001" 

    # mock altri parametri richiesti dalla funzione
    mock_prompt = mocker.Mock()
    mock_enriched_query = mocker.Mock()
    mock_tag_info = mocker.Mock()
    mock_logger = mocker.Mock()
    mock_session = AsyncMock(spec=ClientSession)
    mock_consumer = mocker.Mock(spec=LLMConsumer("test_consumer", "1234567890abcdef"))

    # Act
    result = await check_msd_question(
        request=request,
        tag="domus",
        msd_completion_prompt_data=mock_prompt,
        msd_intent_recognition_prompt_data=mock_prompt,
        language_service=language_service,
        enriched_query=mock_enriched_query,
        completion_prompt_data=mock_prompt,
        tag_info=mock_tag_info,
        logger=mock_logger,
        session=mock_session,
        consumer=mock_consumer
    )

    # Assert
    assert result is None or isinstance(result, RagOrchestratorResponse)  # adatta secondo il comportamento atteso
    #mock_redis.make_key.assert_called_once_with("list", request.conversation_id)
    #mock_redis.get_from_redis.assert_called_once()
