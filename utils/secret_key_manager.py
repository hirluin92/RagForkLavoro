import json
from services.storage import a_get_blob_content_from_container
from aiocache import cached
from models.configurations.keyvault import KeyVaultSettings
from azure.keyvault.secrets.aio import SecretClient
from azure.identity.aio import DefaultAzureCredential
import re
from typing import Tuple, Dict, Optional
import logging

@cached(ttl=600)
async def a_get_config_for_source(source_identifier: str) -> Dict[str, Optional[str]]:
    """
    DEPRECATED: Sostituito da a_get_complete_config in utils.db_config.
    
    Questa funzione mantiene la logica basata su secretmap.json in Key Vault.
    La nuova implementazione usa SQL Server con chiave composta (source_identifier + model_name).
    
    Recupera configurazione completa per il source_identifier dal secretmap.json.
    
    Returns:
        dict con:
        - 'secret': str (chiave API dal KeyVault, o None se Key Vault fallisce)
        - 'model': str | None (deployment model, se presente nel JSON)
        - 'api_version': str | None (legge "version" o "api_version" dal JSON)
    
    Raises:
        ValueError: se source_identifier non trovato nel JSON
    """
    kv_settings = KeyVaultSettings()
    file_content = await a_get_blob_content_from_container(
        kv_settings.secret_map_container_name, 
        kv_settings.secret_map_file_name
    )
    map = json.loads(file_content)

    logger = logging.getLogger(__name__)
    logger.info(f"🔍 Reading secretmap.json: found {len(map)} entries")
    
    # Verifica se source_identifier esiste nel JSON
    found_item = None
    for item in map:
        if item.get("source_identifier") == source_identifier:
            found_item = item
            logger.info(f"✅ Found source_identifier '{source_identifier}' in secretmap.json")
            break
    
    if not found_item:
        raise ValueError(f"no source identifier found for '{source_identifier}' in secretmap.json")

    # Estrai model e api_version dal JSON
    api_version = found_item.get("version") or found_item.get("api_version")
    model = found_item.get("model")
    
    logger.info(f"📦 Config from JSON for '{source_identifier}': model={model}, version={api_version}")

    # Prova a recuperare il secret dal Key Vault
    secret = None
    try:
        keyvault_url = found_item["secret"]
        
        # Estrai vault URL dall'URL del secret
        from urllib.parse import urlparse
        parsed_url = urlparse(keyvault_url)
        vault_url_from_json = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Crea client con vault URL dal JSON
        credential = DefaultAzureCredential()
        kv_client = SecretClient(vault_url=vault_url_from_json, credential=credential)

        # ✅ MANTIENE il doppio async with come nella versione originale di RagForkLavoro
        async with kv_client:
            async with credential:
                _, secret_name, version = extract_keyvault_info(keyvault_url)
                secret_obj = await kv_client.get_secret(secret_name, version)
                
                if secret_obj and secret_obj.value:
                    secret = secret_obj.value
                    logger.info(f"✅ Secret retrieved from Key Vault for '{source_identifier}'")
                else:
                    raise ValueError(f"An empty secret found for {source_identifier}")
                
    except Exception as kv_error:
        logger.warning(f"⚠️ Key Vault failed for '{source_identifier}': {type(kv_error).__name__}. Will use model/version from JSON, but secret must come from fallback.")
        secret = None
    
    return {
        "secret": secret,
        "model": model,
        "api_version": api_version
    }


@cached(ttl=600)
async def a_get_secret_key(source_identifier: str) -> str:
    """
    Retrocompatibilità: ritorna solo il secret (chiave API).
    Internamente usa a_get_config_for_source.
    
    Deprecated: Usa a_get_config_for_source() per ottenere anche model e api_version.
    """
    config = await a_get_config_for_source(source_identifier)
    return config["secret"]


def extract_keyvault_info(input_string: str) -> Tuple[str, str, str]:
    pattern = r"https:\/\/(?P<keyvault_name>[A-z0-9-]+)\.vault.azure.net\/secrets\/(?P<secret_name>[A-z0-9-]+)(\/(?P<version>[A-z0-9]+))?"
    match = re.search(pattern, input_string)
    
    if match:
        keyvault_name = match.group('keyvault_name')
        secret_name = match.group('secret_name')
        version = match.group('version') if match.group('version') else None
        return keyvault_name, secret_name, version  # type: ignore
    else:
        raise ValueError("Error extracting data from keyvault url")