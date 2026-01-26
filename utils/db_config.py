"""
Modulo per gestione configurazione deployment tramite SQL Server e Key Vault.
Sostituisce la logica basata su secretmap.json in Key Vault.
"""

import os
import logging
from typing import Dict, Optional
from aiocache import cached
import aioodbc
import pyodbc
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient

logger = logging.getLogger(__name__)

# Custom Exceptions
class DeploymentNotFoundError(Exception):
    """Combinazione source_identifier + model_name non trovata in dbo.secrets_mapping"""
    pass

class DatabaseConnectionError(Exception):
    """Errore di connessione a SQL Server"""
    pass

class IncompleteConfigError(Exception):
    """Configurazione incompleta (campi NULL)"""
    pass

class SecretRetrievalError(Exception):
    """Errore nel recupero del secret da Key Vault"""
    pass

class InvalidSecretUrlError(Exception):
    """URL del secret malformato o non valido"""
    pass


@cached(ttl=3600)  # Cache 1 ora - deployment config cambiano raramente
async def a_get_deployment_config(
    source_identifier: str,
    model_name: str  # ← NUOVO: deployment name obbligatorio
) -> Dict[str, str]:
    """
    Recupera configurazione deployment da SQL Server usando chiave composta.
    
    Args:
        source_identifier: Identificativo consumer (es: "MS00987")
        model_name: Nome deployment/modello (es: "INPS_gpt4o", "gpt-4.1-mini")
        
    Returns:
        Dict con chiavi: 'deployment', 'api_version', 'secret_url', 'description', 'type'
        
    Raises:
        DeploymentNotFoundError: combinazione source_identifier + model_name non trovata
        DatabaseConnectionError: errore connessione SQL
        IncompleteConfigError: campi NULL nella configurazione
    """
    connection_string = os.getenv("ConnectionStrings_DatabaseSql")
    
    if not connection_string:
        logger.error("ConnectionStrings_DatabaseSql non configurata")
        raise DatabaseConnectionError("ConnectionStrings_DatabaseSql mancante nelle variabili d'ambiente")
    
    try:
        # aioodbc.connect() accetta dsn anche con connection string completa
        async with aioodbc.connect(dsn=connection_string) as conn:
            async with conn.cursor() as cursor:
                # Query con CHIAVE COMPOSTA: source_identifier AND model
                query = """
                    SELECT model, api_version, secret, description, type
                    FROM dbo.secrets_mapping
                    WHERE source_identifier = ? AND model = ?
                """
                await cursor.execute(query, (source_identifier, model_name))
                row = await cursor.fetchone()
                
                if not row:
                    logger.warning(
                        f"Deployment non trovato",
                        extra={
                            "source_identifier": source_identifier,
                            "model_name": model_name
                        }
                    )
                    raise DeploymentNotFoundError(
                        f"Deployment '{model_name}' non configurato per source '{source_identifier}'"
                    )
                
                # Validazione campi obbligatori
                model, api_version, secret, description, type_val = row
                
                missing_fields = []
                if not model:
                    missing_fields.append("model")
                if not api_version:
                    missing_fields.append("api_version")
                if not secret:
                    missing_fields.append("secret")
                
                if missing_fields:
                    logger.error(
                        f"Configurazione incompleta",
                        extra={
                            "source_identifier": source_identifier,
                            "model_name": model_name,
                            "missing_fields": missing_fields
                        }
                    )
                    raise IncompleteConfigError(
                        f"Campi mancanti: {', '.join(missing_fields)}"
                    )
                
                config = {
                    'deployment': model,
                    'api_version': api_version,
                    'secret_url': secret,
                    'description': description or '',
                    'type': type_val or 'llm'
                }
                
                logger.info(
                    f"Configurazione recuperata",
                    extra={
                        "source_identifier": source_identifier,
                        "model_name": model_name,
                        "api_version": api_version
                    }
                )
                
                return config
                
    except DeploymentNotFoundError:
        raise
    except IncompleteConfigError:
        raise
    except (pyodbc.Error, Exception) as e:
        logger.error(
            f"Errore connessione SQL Server",
            extra={
                "source_identifier": source_identifier,
                "model_name": model_name,
                "error": str(e),
                "error_type": type(e).__name__,
                "server": "SQLINPSSVIL150.ser-test.inps:1433",
                "database": "DS06039_GenAISQL"
            },
            exc_info=True
        )
        raise DatabaseConnectionError(f"Errore connessione SQL Server: {str(e)}")
    except Exception as e:
        logger.error(
            f"Errore imprevisto nel recupero configurazione",
            extra={
                "source_identifier": source_identifier,
                "model_name": model_name,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise DatabaseConnectionError(f"Errore imprevisto: {str(e)}")


@cached(ttl=600)  # Cache 10 minuti - API keys possono ruotare
async def a_get_api_key_from_vault(secret_url: str) -> str:
    """
    Recupera API key da Azure Key Vault usando l'URL completo del secret.
    
    Args:
        secret_url: URL completo del secret Key Vault
                   es: "https://az00040-genai1-dev-kvt.vault.azure.net/secrets/OpenAiKey-MS00987/version"
        
    Returns:
        API key string
        
    Raises:
        InvalidSecretUrlError: URL malformato
        SecretRetrievalError: errore nel recupero del secret
    """
    # Validazione URL
    if not secret_url or not secret_url.startswith("https://"):
        logger.error(f"URL secret malformato: {secret_url}")
        raise InvalidSecretUrlError(f"URL secret non valido: {secret_url}")
    
    try:
        # Estrai vault name dall'URL
        # Formato: https://{vault-name}.vault.azure.net/secrets/{secret-name}/{version}
        from urllib.parse import urlparse
        parsed_url = urlparse(secret_url)
        vault_url = f"{parsed_url.scheme}://{parsed_url.netloc}"  # https://{vault-name}.vault.azure.net
        path_parts = parsed_url.path.strip('/').split('/')
        
        if len(path_parts) < 2 or path_parts[0] != 'secrets':
            raise InvalidSecretUrlError("Formato URL secret non valido: deve contenere /secrets/{secret-name}/...")
        
        secret_name = path_parts[1]
        secret_version = path_parts[2] if len(path_parts) > 2 else None
        
        # Usa Managed Identity per autenticazione (async)
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=vault_url, credential=credential)
        
        # Recupera il secret (async)
        async with client:
            async with credential:
                if secret_version:
                    secret = await client.get_secret(secret_name, version=secret_version)
                else:
                    secret = await client.get_secret(secret_name)
                
                if not secret or not secret.value:
                    raise SecretRetrievalError(f"Secret vuoto o non trovato: {secret_name}")
        
        logger.info(
            f"API key recuperata da Key Vault",
            extra={
                "vault_url": vault_url,
                "secret_name": secret_name
            }
        )
        
        return secret.value
        
    except InvalidSecretUrlError:
        raise
    except Exception as e:
        logger.error(
            f"Errore recupero secret da Key Vault",
            extra={
                "secret_url": secret_url,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise SecretRetrievalError(f"Impossibile recuperare secret da Key Vault: {str(e)}")


async def a_get_complete_config(
    source_identifier: str,
    model_name: str  # ← NUOVO: parametro obbligatorio
) -> Dict[str, str]:
    """
    Orchestrazione completa: recupera deployment config da SQL e API key da Key Vault.
    
    Questa è la funzione principale da usare per sostituire a_get_config_for_source().
    
    Args:
        source_identifier: Identificativo consumer
        model_name: Nome deployment/modello
        
    Returns:
        Dict con chiavi: 'deployment', 'api_version', 'api_key', 'description', 'type'
        
    Raises:
        DeploymentNotFoundError, DatabaseConnectionError, IncompleteConfigError,
        InvalidSecretUrlError, SecretRetrievalError
    """
    # Step 1: Query SQL per deployment config (con chiave composta)
    config = await a_get_deployment_config(source_identifier, model_name)
    
    # Step 2: Query Key Vault per API key
    api_key = await a_get_api_key_from_vault(config['secret_url'])
    
    # Step 3: Assembla configurazione completa
    complete_config = {
        'deployment': config['deployment'],
        'api_version': config['api_version'],
        'api_key': api_key,
        'description': config['description'],
        'type': config['type']
    }
    
    return complete_config
