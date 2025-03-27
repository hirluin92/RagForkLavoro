import pytest
from models.apis.convert_docx_to_md_response_body import ValueToAzAISearch, DataToAzAISearch


def test_value_to_azai_search_initialization():
    # Arrange
    record_id = "12345"
    data = DataToAzAISearch(content="Sample content")
    errors = ["Error 1", "Error 2"]
    warnings = ["Warning 1"]

    # Act
    value = ValueToAzAISearch(
        recordId=record_id, data=data, errors=errors, warnings=warnings)

    # Assert
    assert value.recordId == record_id
    assert value.data == data
    assert value.errors == errors
    assert value.warnings == warnings
