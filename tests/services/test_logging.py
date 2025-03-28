import pytest
from unittest.mock import MagicMock, patch
from services.logging import LoggerBuilder, Logger

import azure.functions as func


@pytest.fixture
def mock_context():
    trace_context = MagicMock()
    trace_context.Traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    trace_context.Tracestate = "state"
    context = MagicMock()
    context.trace_context = trace_context
    context.invocation_id = "test-invocation-id"
    return context


def test_logger_methods(mock_context):
    with patch("services.logging.getLogger") as mock_get_logger, \
            patch("services.logging.track_event") as mock_track_event:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        logger = Logger(
            "test-logger", mock_context.invocation_id, "test-operation-id")

        logger.info("Info message")
        mock_logger.info.assert_called_once_with(
            "Info message", extra={"InvocationId": "test-invocation-id"})

        logger.warning("Warning message")
        mock_logger.warning.assert_called_once_with(
            "Warning message", extra={"InvocationId": "test-invocation-id"})

        logger.error("Error message")
        mock_logger.error.assert_called_once_with(
            "Error message", extra={"InvocationId": "test-invocation-id"})

        logger.exception("Exception message")
        mock_logger.exception.assert_called_once_with(
            "Exception message", extra={"InvocationId": "test-invocation-id"})

        logger.track_event("TestEvent", {"key": "value"})
        mock_track_event.assert_called_once_with(
            "TestEvent", {"key": "value", "InvocationId": "test-invocation-id"})
