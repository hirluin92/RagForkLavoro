import json
import azure.functions as func
import pytest
from unittest.mock import Mock
from tests.mock_env import set_mock_env
from tests.mock_logging import set_mock_logger_builder
from check_status import check_status as check_status_endpoint
from health_check import health_check as health_check_endpoint



@pytest.mark.asyncio
async def test_check_status(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)
    set_mock_logger_builder(mocker)

    req = func.HttpRequest(method='GET',
                           headers={'Content-Type': 'application/json'},
                           body=None,
                           url='/api/check-status')

    mock_trace_context = mocker.Mock()

    # Act
    func_call = check_status_endpoint.build().get_user_function()
    response = await func_call(req, mock_trace_context)

    # Assert
    assert response.status_code == 200
    assert response.mimetype == "application/problem+json"
    assert response.get_body().decode() == json.dumps("RAG: OK")

@pytest.mark.asyncio
async def test_health_check(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)

    req = func.HttpRequest(method='GET',
                           headers={'Content-Type': 'application/json'},
                           body=None,
                           url='/api/health')

    mock_trace_context = mocker.Mock()

    # Act
    func_call = health_check_endpoint.build().get_user_function()
    response = await func_call(req, mock_trace_context)

    # Assert
    assert response.status_code == 200
    assert response.mimetype == "application/json"

    expected_body = {"status": "healthy", "version": "v1.0.1"}
    assert json.loads(response.get_body().decode()) == expected_body