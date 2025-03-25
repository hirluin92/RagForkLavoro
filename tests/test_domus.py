import pytest
import json
from unittest.mock import AsyncMock, Mock
from aiohttp import ClientSession, ClientResponse
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
