import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from utils.db_config import (
    a_get_deployment_config,
    a_get_api_key_from_vault,
    a_get_complete_config,
    DeploymentNotFoundError,
    DatabaseConnectionError,
    IncompleteConfigError,
    SecretRetrievalError,
    InvalidSecretUrlError
)


class FakeSecretClient:
    """Fake SecretClient che supporta async context manager"""
    
    def __init__(self, vault_url=None, credential=None, secret_obj=None, get_secret_side_effect=None):
        self.vault_url = vault_url
        self.credential = credential
        self.secret_obj = secret_obj
        self.get_secret_side_effect = get_secret_side_effect
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        return False
    
    async def get_secret(self, secret_name, version=None):
        if self.get_secret_side_effect:
            raise self.get_secret_side_effect
        return self.secret_obj


class FakeDefaultAzureCredential:
    """Fake DefaultAzureCredential che supporta async context manager"""
    
    def __init__(self, *args, **kwargs):
        pass
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        return False


# IMPORTANTE: Clear cache prima di ogni test
@pytest.fixture(autouse=True)
def clear_cache(mocker):
    """Clear aiocache before each test"""
    def passthrough_decorator(ttl=None):
        def decorator(func):
            return func
        return decorator
    
    mocker.patch("utils.db_config.cached", passthrough_decorator)
    
    # Clear cache se esiste
    try:
        from aiocache import caches
        caches.get('default').clear()
    except:
        pass
    
    yield
    
    try:
        from aiocache import caches
        caches.get('default').clear()
    except:
        pass


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch, request):
    """Mock ConnectionStrings_DatabaseSql environment variable (skip for test_get_deployment_config_missing_env_var)"""
    # Skip per test_get_deployment_config_missing_env_var che deve testare la mancanza della variabile
    # Controlla sia il nome del test che eventuali marker
    test_name = getattr(request.node, 'originalname', None) or request.node.name
    # Controlla anche se il test ha un marker specifico
    skip_marker = request.node.get_closest_marker("skip_mock_env")
    if "test_get_deployment_config_missing_env_var" not in test_name and skip_marker is None:
        monkeypatch.setenv("ConnectionStrings_DatabaseSql", "Server=test;Database=test;User=test;Password=test")


@pytest.mark.asyncio
async def test_get_deployment_config_success():
    """Test recupero config da SQL con chiave composta"""
    mock_row = (
        "INPS_gpt4o",  # model
        "2024-08-01-preview",  # api_version
        "https://az00040-genai1-dev-kvt.vault.azure.net/secrets/OpenAiKey-MS00987/abc",  # secret
        "Test description",  # description
        "llm"  # type
    )
    
    with patch('aioodbc.connect') as mock_connect:
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)
        mock_cursor.execute = AsyncMock()
        mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor.__aexit__ = AsyncMock(return_value=None)
        
        mock_conn = AsyncMock()
        mock_conn.cursor = MagicMock(return_value=mock_cursor)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        
        # Mock aioodbc.connect come context manager
        mock_connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_connect.return_value.__aexit__ = AsyncMock(return_value=None)
        
        config = await a_get_deployment_config("MS00987", "INPS_gpt4o")
        
        # Verifica che la query abbia usato ENTRAMBI i parametri
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "WHERE source_identifier = ? AND model = ?" in call_args[0][0]
        assert call_args[0][1] == ("MS00987", "INPS_gpt4o")
        
        assert config['deployment'] == "INPS_gpt4o"
        assert config['api_version'] == "2024-08-01-preview"
        assert config['secret_url'] == "https://az00040-genai1-dev-kvt.vault.azure.net/secrets/OpenAiKey-MS00987/abc"
        assert config['description'] == "Test description"
        assert config['type'] == "llm"


@pytest.mark.asyncio
async def test_get_deployment_config_not_found():
    """Test combinazione source_identifier + model_name non trovata"""
    with patch('aioodbc.connect') as mock_connect:
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)
        mock_cursor.execute = AsyncMock()
        mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor.__aexit__ = AsyncMock(return_value=None)
        
        mock_conn = AsyncMock()
        mock_conn.cursor = MagicMock(return_value=mock_cursor)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        
        # Mock aioodbc.connect come context manager
        mock_connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_connect.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with pytest.raises(DeploymentNotFoundError) as exc_info:
            await a_get_deployment_config("MS00987", "NON_EXISTING_MODEL")
        
        assert "NON_EXISTING_MODEL" in str(exc_info.value)
        assert "MS00987" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_deployment_different_models_same_source():
    """Test stesso source_identifier con modelli diversi"""
    # Simula MS00987 con INPS_gpt4o
    mock_row_1 = ("INPS_gpt4o", "2024-08-01-preview", "https://kvt.../secret1", "Chat", "llm")
    
    # Simula MS00987 con gpt-4.1-mini (embedding)
    mock_row_2 = ("gpt-4.1-mini", "2024-08-01-preview", "https://kvt.../secret2", "Embedding", "embedding")
    
    with patch('aioodbc.connect') as mock_connect:
        # Prima chiamata: INPS_gpt4o
        mock_cursor_1 = AsyncMock()
        mock_cursor_1.fetchone = AsyncMock(return_value=mock_row_1)
        mock_cursor_1.execute = AsyncMock()
        mock_cursor_1.__aenter__ = AsyncMock(return_value=mock_cursor_1)
        mock_cursor_1.__aexit__ = AsyncMock()
        
        mock_conn_1 = AsyncMock()
        mock_conn_1.cursor = MagicMock(return_value=mock_cursor_1)
        mock_conn_1.__aenter__ = AsyncMock(return_value=mock_conn_1)
        mock_conn_1.__aexit__ = AsyncMock()
        
        mock_connect.return_value = mock_conn_1
        
        config1 = await a_get_deployment_config("MS00987", "INPS_gpt4o")
        assert config1['deployment'] == "INPS_gpt4o"
        assert config1['type'] == "llm"
        
        # Seconda chiamata: gpt-4.1-mini
        mock_cursor_2 = AsyncMock()
        mock_cursor_2.fetchone = AsyncMock(return_value=mock_row_2)
        mock_cursor_2.execute = AsyncMock()
        mock_cursor_2.__aenter__ = AsyncMock(return_value=mock_cursor_2)
        mock_cursor_2.__aexit__ = AsyncMock()
        
        mock_conn_2 = AsyncMock()
        mock_conn_2.cursor = MagicMock(return_value=mock_cursor_2)
        mock_conn_2.__aenter__ = AsyncMock(return_value=mock_conn_2)
        mock_conn_2.__aexit__ = AsyncMock()
        
        mock_connect.return_value = mock_conn_2
        
        config2 = await a_get_deployment_config("MS00987", "gpt-4.1-mini")
        assert config2['deployment'] == "gpt-4.1-mini"
        assert config2['type'] == "embedding"


@pytest.mark.asyncio
async def test_get_deployment_config_incomplete_config():
    """Test configurazione con campi NULL"""
    mock_row = (
        "INPS_gpt4o",  # model
        None,  # api_version NULL
        "https://kvt.../secret",  # secret
        "Description",  # description
        "llm"  # type
    )
    
    # Crea un mock context manager per aioodbc.connect()
    mock_conn_context = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.fetchone = AsyncMock(return_value=mock_row)
    mock_cursor.execute = AsyncMock()
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=None)
    
    mock_conn = AsyncMock()
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    
    mock_conn_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn_context.__aexit__ = AsyncMock(return_value=None)
    
    with patch('aioodbc.connect', return_value=mock_conn_context):
        with pytest.raises(IncompleteConfigError) as exc_info:
            await a_get_deployment_config("MS00987", "INPS_gpt4o")
        
        assert "api_version" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_api_key_from_vault_success(monkeypatch):
    """Test recupero API key da Key Vault"""
    mock_secret = MagicMock()
    mock_secret.value = "api-key-xyz"
    
    monkeypatch.setattr("utils.db_config.SecretClient", lambda vault_url, credential: FakeSecretClient(
        vault_url=vault_url, 
        credential=credential, 
        secret_obj=mock_secret
    ))
    monkeypatch.setattr("utils.db_config.DefaultAzureCredential", lambda *args, **kwargs: FakeDefaultAzureCredential(*args, **kwargs))
    
    secret_url = "https://az00040-genai1-dev-kvt.vault.azure.net/secrets/OpenAiKey-MS00987/abc"
    api_key = await a_get_api_key_from_vault(secret_url)
    
    assert api_key == "api-key-xyz"


@pytest.mark.asyncio
async def test_get_api_key_from_vault_invalid_url():
    """Test URL secret malformato"""
    with pytest.raises(InvalidSecretUrlError) as exc_info:
        await a_get_api_key_from_vault("invalid-url")
    
    assert "non valido" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_api_key_from_vault_missing_version(monkeypatch):
    """Test recupero secret senza versione specificata"""
    mock_secret = MagicMock()
    mock_secret.value = "api-key-xyz"
    
    monkeypatch.setattr("utils.db_config.SecretClient", lambda vault_url, credential: FakeSecretClient(
        vault_url=vault_url, 
        credential=credential, 
        secret_obj=mock_secret
    ))
    monkeypatch.setattr("utils.db_config.DefaultAzureCredential", lambda *args, **kwargs: FakeDefaultAzureCredential(*args, **kwargs))
    
    # URL senza versione
    secret_url = "https://az00040-genai1-dev-kvt.vault.azure.net/secrets/OpenAiKey-MS00987"
    api_key = await a_get_api_key_from_vault(secret_url)
    
    assert api_key == "api-key-xyz"


@pytest.mark.asyncio
async def test_get_complete_config_with_model_name(monkeypatch):
    """Test orchestrazione completa con model_name"""
    mock_sql_row = (
        "INPS_gpt4o",
        "2024-08-01-preview",
        "https://az00040-genai1-dev-kvt.vault.azure.net/secrets/OpenAiKey-MS00987/abc",
        "Description",
        "llm"
    )
    
    mock_secret = MagicMock()
    mock_secret.value = "api-key-xyz"
    
    # Crea un mock context manager per aioodbc.connect()
    mock_conn_context = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.fetchone = AsyncMock(return_value=mock_sql_row)
    mock_cursor.execute = AsyncMock()
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=None)
    
    mock_conn = AsyncMock()
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    
    mock_conn_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn_context.__aexit__ = AsyncMock(return_value=None)
    
    with patch('aioodbc.connect', return_value=mock_conn_context):
        # Setup Key Vault mock
        monkeypatch.setattr("utils.db_config.SecretClient", lambda vault_url, credential: FakeSecretClient(
            vault_url=vault_url, 
            credential=credential, 
            secret_obj=mock_secret
        ))
        monkeypatch.setattr("utils.db_config.DefaultAzureCredential", lambda *args, **kwargs: FakeDefaultAzureCredential(*args, **kwargs))
        
        # Test con model_name
        config = await a_get_complete_config("MS00987", "INPS_gpt4o")
        
        # Verifica parametri query SQL
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert call_args[0][1] == ("MS00987", "INPS_gpt4o")
        
        assert config['deployment'] == "INPS_gpt4o"
        assert config['api_version'] == "2024-08-01-preview"
        assert config['api_key'] == "api-key-xyz"
        assert config['description'] == "Description"
        assert config['type'] == "llm"


@pytest.mark.asyncio
async def test_get_deployment_config_database_error(monkeypatch):
    """Test errore connessione database"""
    import pyodbc
    
    monkeypatch.setenv("ConnectionStrings_DatabaseSql", "Driver={ODBC Driver 17 for SQL Server};Server=tcp:test,1433;Database=test;Uid=test;Pwd=test;")
    
    # Crea un mock context manager che solleva un errore quando viene entrato
    mock_conn_context = AsyncMock()
    mock_conn_context.__aenter__ = AsyncMock(side_effect=pyodbc.Error("Connection failed"))
    mock_conn_context.__aexit__ = AsyncMock(return_value=None)
    
    with patch('aioodbc.connect', return_value=mock_conn_context):
        with pytest.raises(DatabaseConnectionError) as exc_info:
            await a_get_deployment_config("MS00987", "INPS_gpt4o")
        
        assert "Connection failed" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.skip_mock_env
async def test_get_deployment_config_missing_env_var(monkeypatch):
    """Test mancanza ConnectionStrings_DatabaseSql"""
    # Mock os.getenv nel modulo utils.db_config per restituire None quando viene chiamato con ConnectionStrings_DatabaseSql
    # Questo bypassa completamente il problema del fixture autouse
    from utils import db_config
    import os
    
    original_getenv = os.getenv
    
    def mock_getenv(key, default=None):
        if key == "ConnectionStrings_DatabaseSql":
            return None
        return original_getenv(key, default)
    
    # Mock os.getenv nel modulo db_config usando monkeypatch
    monkeypatch.setattr(db_config.os, "getenv", mock_getenv)
    
    with pytest.raises(DatabaseConnectionError) as exc_info:
        await a_get_deployment_config("MS00987", "INPS_gpt4o")
    
    assert "ConnectionStrings_DatabaseSql" in str(exc_info.value)
