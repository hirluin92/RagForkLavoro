import json
import azure.functions as func
import pytest
from pydantic import ValidationError
from unittest.mock import AsyncMock
from tests.mock_env import set_mock_env
from tests.mock_logging import set_mock_logger_builder
from logics.convert_docx_to_md import a_extract_hyperlink_from_files
from utils.settings import get_storage_settings
from convert_docx_to_md import convert_docx_to_md as convert_docx_to_md_endpoint
from models.apis.convert_docx_to_md_request_body import ConvertDocxToMdRequestBody

@pytest.mark.asyncio
async def test_convert_docx_to_md_no_body(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)
    set_mock_logger_builder(mocker)

    req = func.HttpRequest(method='POST',
                           headers={'Content-Type': 'application/json'},
                           body=None,
                           url='/api/convertDocxToMd')

    mock_trace_context = mocker.Mock()

    # Act
    func_call = convert_docx_to_md_endpoint.build().get_user_function()
    response = await func_call(req, mock_trace_context)

    # Assert
    assert response.status_code == 500

import json
import azure.functions as func
import pytest
from unittest.mock import Mock
from tests.mock_env import set_mock_env
from tests.mock_logging import set_mock_logger_builder
from convert_docx_to_md import convert_docx_to_md as convert_docx_to_md_endpoint


@pytest.mark.asyncio
async def test_convert_docx_to_md_invalid_storage_config(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)
    set_mock_logger_builder(mocker)

    # Patch di get_storage_settings per generare un errore simulato
    mocker.patch("utils.settings.get_storage_settings", side_effect=ValueError("Storage config missing"))

    req_body = {
        "file_data": "dummy_base64_content"
    }
    req = func.HttpRequest(method='POST',
                           headers={'Content-Type': 'application/json'},
                           body=bytes(json.dumps(req_body), "utf-8"),
                           url='/api/convertDocxToMd')

    mock_trace_context = mocker.Mock()

    # Act
    func_call = convert_docx_to_md_endpoint.build().get_user_function()
    response = await func_call(req, mock_trace_context)

    # Assert
    assert response.status_code == 422 

@pytest.mark.asyncio
async def test_convert_docx_to_md_missing_body_value(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)
    set_mock_logger_builder(mocker)

    req_body = {}  # Body vuoto, quindi non valido
    req = func.HttpRequest(method='POST',
                           headers={'Content-Type': 'application/json'},
                           body=bytes(json.dumps(req_body), "utf-8"),
                           url='/api/convertDocxToMd')

    mock_trace_context = mocker.Mock()

    # Act
    func_call = convert_docx_to_md_endpoint.build().get_user_function()
    response = await func_call(req, mock_trace_context)

    # Assert
    assert response.status_code == 422
