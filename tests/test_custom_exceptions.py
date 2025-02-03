from exceptions.custom_exceptions import CustomPromptParameterError

def test_custom_prompt_parameter_error_message():
    error = CustomPromptParameterError("Test message", 404)
    assert error.message == "Test message"
    assert str(error) == "Test message"

def test_custom_prompt_parameter_error_code():
    error = CustomPromptParameterError("Test message", 404)
    assert error.error_code == 404