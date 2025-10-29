import pytest
from unittest.mock import patch, MagicMock
from services.redis import get_from_redis, set_to_redis, make_key, get_all_keys_by_conv_id

import azure.functions as func


@pytest.fixture
# Test per make_key
def test_make_key_list():
    assert make_key("list", "ABC123") == "list_abc123"

def test_make_key_dett_with_dettid():
    assert make_key("dett", "ABC123", "DET456") == "dett_abc123_DET456"

def test_make_key_invalid_prefix():
    with pytest.raises(ValueError):
        make_key("invalid", "ABC123")

# Test per get_from_redis
@patch("services.redis.Redis")
@patch("services.redis.RedisSettings")
def test_get_from_redis(mock_settings, mock_redis):
    mock_settings.return_value = MagicMock(
        host="localhost", port=6379, password="", ssl=False
    )
    mock_instance = MagicMock()
    mock_instance.get.return_value = "test_value"
    mock_redis.return_value = mock_instance

    result = get_from_redis("MyKey")
    assert result == "test_value"
    mock_instance.get.assert_called_with("mykey")

# Test per set_to_redis
@patch("services.redis.Redis")
@patch("services.redis.RedisSettings")
def test_set_to_redis(mock_settings, mock_redis):
    mock_settings.return_value = MagicMock(
        host="localhost", port=6379, password="", ssl=False, expiration_seconds=60
    )
    mock_instance = MagicMock()
    mock_redis.return_value = mock_instance

    set_to_redis("MyKey", "MyValue")
    mock_instance.set.assert_called_with("mykey", "MyValue", ex=60)

# Test per get_all_keys_by_conv_id
@patch("services.redis.Redis")
@patch("services.redis.RedisSettings")
def test_get_all_keys_by_conv_id(mock_settings, mock_redis):
    mock_settings.return_value = MagicMock(
        host="localhost", port=6379, password="", ssl=False
    )
    mock_instance = MagicMock()
    mock_instance.scan_iter.return_value = ["list_abc123", "dett_abc123_DET456", "other_key"]
    mock_redis.return_value = mock_instance

    result = get_all_keys_by_conv_id("abc123")
    assert "list_abc123" in result
    assert "dett_abc123_DET456" in result
    assert "other_key" not in result