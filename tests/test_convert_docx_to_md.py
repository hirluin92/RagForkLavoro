import json
import io
from pydantic import ValidationError
import pytest
import azure.functions as func
from tests.mock_env import set_mock_env
from tests.mock_logging import MockLogger, set_mock_logger_builder
from tests.mock_logging import set_mock_logger_builder
from tests.mock_env import set_mock_env
from logics.convert_docx_to_md import a_extract_hyperlink_from_files


@pytest.mark.asyncio
async def test_a_extract_hyperlink_from_docx_ok(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)
    set_mock_logger_builder(mocker)
    mock_logger = MockLogger()
    mock_value_data = mocker.Mock()
    mock_value_data.fileUrl = "https://local.blob.core.windows.net/data1/auu/assegno_unico_prova.docx"
    mock_value_data.fileSasToken = "?sasToken"

    mock_value = mocker.Mock()
    mock_value.recordId = "123"
    mock_value.data = mock_value_data

    mock_data = mocker.Mock()
    mock_data.values = [mock_value]

    blob_client = mocker.Mock()
    mocker.patch("logics.convert_docx_to_md.get_blob_client_from_blob_storage_path",
                 return_value=blob_client)

    mocker.patch("logics.convert_docx_to_md.generate_blob_sas_from_blob_client",
                 return_value="mysastoken")

    mocker.patch("logics.convert_docx_to_md.get_blob_info_container_and_blobName",
                 return_value=("container", "file.docx"))

    mock_text_content = io.StringIO("some initial text data")
    mocker.patch("logics.convert_docx_to_md.a_get_blob_stream_from_container",
                 return_value=mock_text_content)

    data_text_mock = "some initial text data"

    mocker.patch("logics.convert_docx_to_md.extract_text_and_hyperlink_from_docx",
                 return_value=data_text_mock)

    # Act
    results = await a_extract_hyperlink_from_files(mock_data, mock_logger)

    # Assert
    assert len(results.values) == 1
    result = results.values[0]
    assert result.recordId == '123'
    assert result.errors is None
    assert result.warnings is None

@pytest.mark.asyncio
async def test_a_extract_hyperlink_from_html_ok(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)
    set_mock_logger_builder(mocker)
    mock_logger = MockLogger()
    mock_value_data = mocker.Mock()
    mock_value_data.fileUrl = "https://local.blob.core.windows.net/data1/auu/assegno_unico_prova.html"
    mock_value_data.fileSasToken = "?sasToken"

    mock_value = mocker.Mock()
    mock_value.recordId = "123"
    mock_value.data = mock_value_data

    mock_data = mocker.Mock()
    mock_data.values = [mock_value]

    blob_client = mocker.Mock()
    mocker.patch("logics.convert_docx_to_md.get_blob_client_from_blob_storage_path",
                 return_value=blob_client)

    mocker.patch("logics.convert_docx_to_md.generate_blob_sas_from_blob_client",
                 return_value="mysastoken")

    mocker.patch("logics.convert_docx_to_md.get_blob_info_container_and_blobName",
                 return_value=("container", "file.html"))

    mock_text_content = io.StringIO("some initial text data")
    mocker.patch("logics.convert_docx_to_md.a_get_blob_stream_from_container",
                 return_value=mock_text_content)

    data_text_mock = "some initial text data"

    mocker.patch("logics.convert_docx_to_md.extract_text_and_hyperlink_from_html",
                 return_value=data_text_mock)

    # Act
    results = await a_extract_hyperlink_from_files(mock_data, mock_logger)

    # Assert
    assert len(results.values) == 1
    result = results.values[0]
    assert result.recordId == '123'
    assert result.errors is None
    assert result.warnings is None

@pytest.mark.asyncio
async def test_a_extract_hyperlink_from_files_error(mocker, monkeypatch):
    # Arrange
    set_mock_env(monkeypatch)
    set_mock_logger_builder(mocker)
    mock_logger = MockLogger()
    mock_value_data = mocker.Mock()
    mock_value_data.fileUrl = "https://local.blob.core.windows.net/data1/auu/assegno_unico_prova.docx"
    mock_value_data.fileSasToken = "?sasToken"

    mock_value = mocker.Mock()
    mock_value.recordId = "123"
    mock_value.data = mock_value_data

    mock_data = mocker.Mock()
    mock_data.values = [mock_value]

    mocker.patch("logics.convert_docx_to_md.get_blob_info_container_and_blobName",
                 return_value=("container", "name"))

    mock_text_content = io.StringIO("some initial text data")
    mocker.patch("logics.convert_docx_to_md.a_get_blob_stream_from_container",
                 return_value=mock_text_content)

    data_text_mock = "some initial text data"

    exception = Exception('error')
    mocker.patch("logics.convert_docx_to_md.a_extract_hyperlink_from_files",
                 side_effect=exception)

    # Act
    results = await a_extract_hyperlink_from_files(mock_data, mock_logger)

    # Assert
    assert len(results.values) == 1
    result = results.values[0]
    assert result.recordId == '123'
    assert result.errors is not None
    assert result.warnings is None
