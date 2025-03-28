import json
import io
from pydantic import ValidationError
import pytest
import azure.functions as func
from tests.mock_env import set_mock_env
from tests.mock_logging import MockLogger, set_mock_logger_builder
from tests.mock_logging import set_mock_logger_builder
from tests.mock_env import set_mock_env
from logics.convert_docx_to_md import a_extract_hyperlink_from_files, extract_text_and_hyperlink_from_html, get_hyperlink_into_md
import io
import pytest
from logics.convert_docx_to_md import extract_text_and_hyperlink_from_docx


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


def test_extract_text_and_hyperlink_from_docx_with_valid_docx(mocker):
    # Arrange
    mock_stream = io.BytesIO(b"dummy docx content")
    mock_result = mocker.Mock()
    mock_result.value = "<p>Sample text with <a href='http://example.com'>link</a></p>"
    mocker.patch("logics.convert_docx_to_md.mammoth.convert_to_html", return_value=mock_result)
    mock_get_hyperlink_into_md = mocker.patch("logics.convert_docx_to_md.get_hyperlink_into_md", return_value="Sample text with [link](http://example.com)")

    # Act
    result = extract_text_and_hyperlink_from_docx(mock_stream)

    # Assert
    assert result == "Sample text with [link](http://example.com)"
    mock_get_hyperlink_into_md.assert_called_once_with("<p>Sample text with <a href='http://example.com'>link</a></p>")

def test_extract_text_and_hyperlink_from_docx_with_empty_docx(mocker):
    # Arrange
    mock_stream = io.BytesIO(b"")
    mock_result = mocker.Mock()
    mock_result.value = ""
    mocker.patch("logics.convert_docx_to_md.mammoth.convert_to_html", return_value=mock_result)
    mock_get_hyperlink_into_md = mocker.patch("logics.convert_docx_to_md.get_hyperlink_into_md", return_value="")

    # Act
    result = extract_text_and_hyperlink_from_docx(mock_stream)

    # Assert
    assert result == ""
    mock_get_hyperlink_into_md.assert_called_once_with("")

def test_extract_text_and_hyperlink_from_docx_with_invalid_docx(mocker):
    # Arrange
    mock_stream = io.BytesIO(b"invalid docx content")
    mocker.patch("logics.convert_docx_to_md.mammoth.convert_to_html", side_effect=Exception("Invalid docx format"))

    # Act & Assert
    with pytest.raises(Exception, match="Invalid docx format"):
        extract_text_and_hyperlink_from_docx(mock_stream)

        
def test_extract_text_and_hyperlink_from_html_with_valid_html(mocker):
    # Arrange
    mock_stream = io.BytesIO(b"<html><body>Sample text with <a href='http://example.com'>link</a></body></html>")
    mock_get_hyperlink_into_md = mocker.patch(
        "logics.convert_docx_to_md.get_hyperlink_into_md",
        return_value="Sample text with [link](http://example.com)"
    )

    # Act
    result = extract_text_and_hyperlink_from_html(mock_stream)

    # Assert
    assert result == "Sample text with [link](http://example.com)"
    mock_get_hyperlink_into_md.assert_called_once_with(
        "<html><body>Sample text with <a href='http://example.com'>link</a></body></html>"
    )


def test_extract_text_and_hyperlink_from_html_with_empty_html(mocker):
    # Arrange
    mock_stream = io.BytesIO(b"")
    mock_get_hyperlink_into_md = mocker.patch(
        "logics.convert_docx_to_md.get_hyperlink_into_md",
        return_value=""
    )

    # Act
    result = extract_text_and_hyperlink_from_html(mock_stream)

    # Assert
    assert result == ""
    mock_get_hyperlink_into_md.assert_called_once_with("")


def test_extract_text_and_hyperlink_from_html_with_invalid_html(mocker):
    # Arrange
    mock_stream = io.BytesIO(b"<html><body>Invalid HTML content")
    mock_get_hyperlink_into_md = mocker.patch(
        "logics.convert_docx_to_md.get_hyperlink_into_md",
        return_value="Invalid HTML content"
    )

    # Act
    result = extract_text_and_hyperlink_from_html(mock_stream)

    # Assert
    assert result == "Invalid HTML content"
    mock_get_hyperlink_into_md.assert_called_once_with("<html><body>Invalid HTML content")
def test_get_hyperlink_into_md_with_valid_html(mocker):
    # Arrange
    html_text = "<p>Sample text with <a href='http://example.com'>link</a></p>"
    expected_result = "Sample text with [link](http://example.com)"

    # Act
    result = get_hyperlink_into_md(html_text)

    # Assert
    assert result == expected_result


def test_get_hyperlink_into_md_with_multiple_links(mocker):
    # Arrange
    html_text = "<p>Text with <a href='http://example1.com'>link1</a> and <a href='http://example2.com'>link2</a></p>"
    expected_result = "Text with [link1](http://example1.com) and [link2](http://example2.com)"

    # Act
    result = get_hyperlink_into_md(html_text)

    # Assert
    assert result == expected_result


def test_get_hyperlink_into_md_with_empty_links(mocker):
    # Arrange
    html_text = "<p>Text with <a href='http://example.com'></a> and <a href='http://example2.com'>link2</a></p>"
    expected_result = "Text with and [link2](http://example2.com)"

    # Act
    result = get_hyperlink_into_md(html_text)

    # Assert
    assert result == expected_result


def test_get_hyperlink_into_md_with_no_links(mocker):
    # Arrange
    html_text = "<p>Sample text with no links</p>"
    expected_result = "Sample text with no links"

    # Act
    result = get_hyperlink_into_md(html_text)

    # Assert
    assert result == expected_result


def test_get_hyperlink_into_md_with_special_characters(mocker):
    # Arrange
    html_text = "<p>Text with <a href='http://example.com'>link & special</a></p>"
    expected_result = "Text with [link & special](http://example.com)"

    # Act
    result = get_hyperlink_into_md(html_text)

    # Assert
    assert result == expected_result


def test_get_hyperlink_into_md_with_nonbreaking_space(mocker):
    # Arrange
    html_text = "<p>Text&nbsp;with&nbsp;<a href='http://example.com'>link</a></p>"
    expected_result = "Textwith [link](http://example.com)"

    # Act
    result = get_hyperlink_into_md(html_text)

    # Assert
    assert result == expected_result


def test_get_hyperlink_into_md_with_invalid_html(mocker):
    # Arrange
    html_text = "<p>Text with <a href='http://example.com'>link"
    expected_result = "Text with [link](http://example.com)"

    # Act
    result = get_hyperlink_into_md(html_text)

    # Assert
    assert result == expected_result



