import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from utils.secret_key_manager import a_get_config_for_source, a_get_secret_key, extract_keyvault_info


def async_return(result):
    """Helper per creare una coroutine che ritorna un valore"""
    async def _async_return(*args, **kwargs):
        return result
    return _async_return


@pytest.fixture(autouse=True)
def disable_cache(mocker):
    """Disabilita il decorator @cached per tutti i test"""
    def passthrough_decorator(ttl=None):
        def decorator(func):
            return func
        return decorator
    
    mocker.patch("utils.secret_key_manager.cached", passthrough_decorator)


@pytest.mark.asyncio
async def test_a_get_config_for_source_success(mocker):
    """Test che a_get_config_for_source recupera correttamente model e api_version dal JSON"""
    # Mock KeyVaultSettings
    mock_kv_settings = MagicMock()
    mock_kv_settings.secret_map_container_name = "test-container"
    mock_kv_settings.secret_map_file_name = "secretmap.json"
    mocker.patch("utils.secret_key_manager.KeyVaultSettings", return_value=mock_kv_settings)
    
    # Mock blob storage
    mocker.patch(
        "utils.secret_key_manager.a_get_blob_content_from_container",
        return_value='[{"source_identifier": "test-service", "secret": "https://test-vault.vault.azure.net/secrets/test-secret/version123", "model": "gpt-4o", "api_version": "2024-08-01-preview"}]'
    )

    # Mock Key Vault
    mock_secret_obj = MagicMock()
    mock_secret_obj.value = "test-secret-value"

    mock_kv_client = AsyncMock()
    mock_kv_client.get_secret = AsyncMock(return_value=mock_secret_obj)
    mock_kv_client.__aenter__ = AsyncMock(return_value=mock_kv_client)
    mock_kv_client.__aexit__ = AsyncMock(return_value=None)

    mock_credential = AsyncMock()
    mock_credential.__aenter__ = AsyncMock(return_value=mock_credential)
    mock_credential.__aexit__ = AsyncMock(return_value=None)

    mocker.patch("utils.secret_key_manager.SecretClient", return_value=mock_kv_client)
    mocker.patch("utils.secret_key_manager.DefaultAzureCredential", return_value=mock_credential)

    # Act
    result = await a_get_config_for_source("test-service")

    # Assert
    assert result["secret"] == "test-secret-value"
    assert result["model"] == "gpt-4o"
    assert result["api_version"] == "2024-08-01-preview"


@pytest.mark.asyncio
async def test_a_get_config_for_source_with_version_field(mocker):
    """Test che a_get_config_for_source supporta anche il campo 'version' oltre 'api_version'"""
    # Mock KeyVaultSettings
    mock_kv_settings = MagicMock()
    mock_kv_settings.secret_map_container_name = "test-container"
    mock_kv_settings.secret_map_file_name = "secretmap.json"
    mocker.patch("utils.secret_key_manager.KeyVaultSettings", return_value=mock_kv_settings)
    
    # Mock blob storage
    mocker.patch(
        "utils.secret_key_manager.a_get_blob_content_from_container",
        return_value='[{"source_identifier": "test-service", "secret": "https://test-vault.vault.azure.net/secrets/test-secret", "model": "gpt-4o-mini", "version": "2024-02-15-preview"}]'
    )

    # Mock Key Vault
    mock_secret_obj = MagicMock()
    mock_secret_obj.value = "test-secret"

    mock_kv_client = AsyncMock()
    mock_kv_client.get_secret = AsyncMock(return_value=mock_secret_obj)
    mock_kv_client.__aenter__ = AsyncMock(return_value=mock_kv_client)
    mock_kv_client.__aexit__ = AsyncMock(return_value=None)

    mock_credential = AsyncMock()
    mock_credential.__aenter__ = AsyncMock(return_value=mock_credential)
    mock_credential.__aexit__ = AsyncMock(return_value=None)

    mocker.patch("utils.secret_key_manager.SecretClient", return_value=mock_kv_client)
    mocker.patch("utils.secret_key_manager.DefaultAzureCredential", return_value=mock_credential)

    # Act
    result = await a_get_config_for_source("test-service")

    # Assert
    assert result["api_version"] == "2024-02-15-preview"
    assert result["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_a_get_config_for_source_not_found(mocker):
    """Test che a_get_config_for_source solleva ValueError se source_identifier non trovato"""
    # Mock KeyVaultSettings
    mock_kv_settings = MagicMock()
    mock_kv_settings.secret_map_container_name = "test-container"
    mock_kv_settings.secret_map_file_name = "secretmap.json"
    mocker.patch("utils.secret_key_manager.KeyVaultSettings", return_value=mock_kv_settings)
    
    # Mock blob storage
    mocker.patch(
        "utils.secret_key_manager.a_get_blob_content_from_container",
        return_value='[{"source_identifier": "other-service", "secret": "https://test-vault.vault.azure.net/secrets/test-secret"}]'
    )

    # Act & Assert
    with pytest.raises(ValueError, match="no source identifier found"):
        await a_get_config_for_source("test-service")


@pytest.mark.asyncio
async def test_a_get_config_for_source_keyvault_failure(mocker):
    """Test che a_get_config_for_source gestisce correttamente il fallimento del Key Vault"""
    # Mock KeyVaultSettings
    mock_kv_settings = MagicMock()
    mock_kv_settings.secret_map_container_name = "test-container"
    mock_kv_settings.secret_map_file_name = "secretmap.json"
    mocker.patch("utils.secret_key_manager.KeyVaultSettings", return_value=mock_kv_settings)
    
    # Mock blob storage
    mocker.patch(
        "utils.secret_key_manager.a_get_blob_content_from_container",
        return_value='[{"source_identifier": "test-service", "secret": "https://test-vault.vault.azure.net/secrets/test-secret", "model": "gpt-4o", "api_version": "2024-08-01-preview"}]'
    )

    # Mock Key Vault per sollevare un'eccezione
    mock_kv_client = AsyncMock()
    mock_kv_client.get_secret = AsyncMock(side_effect=Exception("Key Vault error"))
    mock_kv_client.__aenter__ = AsyncMock(return_value=mock_kv_client)
    mock_kv_client.__aexit__ = AsyncMock(return_value=None)

    mock_credential = AsyncMock()
    mock_credential.__aenter__ = AsyncMock(return_value=mock_credential)
    mock_credential.__aexit__ = AsyncMock(return_value=None)

    mocker.patch("utils.secret_key_manager.SecretClient", return_value=mock_kv_client)
    mocker.patch("utils.secret_key_manager.DefaultAzureCredential", return_value=mock_credential)

    # Act
    result = await a_get_config_for_source("test-service")

    # Assert
    assert result["secret"] is None
    assert result["model"] == "gpt-4o"
    assert result["api_version"] == "2024-08-01-preview"


@pytest.mark.asyncio
async def test_a_get_secret_key_retrocompatibility(mocker):
    """Test che a_get_secret_key mantiene la retrocompatibilità"""
    # Arrange
    mocker.patch(
        "utils.secret_key_manager.a_get_config_for_source",
        return_value={
            "secret": "test-secret-value",
            "model": "gpt-4o",
            "api_version": "2024-08-01-preview"
        }
    )

    # Act
    result = await a_get_secret_key("test-service")

    # Assert
    assert result == "test-secret-value"


def test_extract_keyvault_info_with_version():
    """Test extract_keyvault_info con versione"""
    keyvault_url = "https://test-vault.vault.azure.net/secrets/test-secret/version123"
    keyvault_name, secret_name, version = extract_keyvault_info(keyvault_url)

    assert keyvault_name == "test-vault"
    assert secret_name == "test-secret"
    assert version == "version123"


def test_extract_keyvault_info_without_version():
    """Test extract_keyvault_info senza versione"""
    keyvault_url = "https://test-vault.vault.azure.net/secrets/test-secret"
    keyvault_name, secret_name, version = extract_keyvault_info(keyvault_url)

    assert keyvault_name == "test-vault"
    assert secret_name == "test-secret"
    assert version is None


def test_extract_keyvault_info_invalid_url():
    """Test extract_keyvault_info con URL non valido"""
    with pytest.raises(ValueError, match="Error extracting data from keyvault url"):
        extract_keyvault_info("invalid-url")