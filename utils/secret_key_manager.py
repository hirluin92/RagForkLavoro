import json
from services.storage import a_get_blob_content_from_container
from aiocache import cached
from models.configurations.keyvault import KeyVaultSettings
from azure.keyvault.secrets.aio import SecretClient
from azure.identity.aio import DefaultAzureCredential
import re
from typing import Tuple

@cached(ttl=600)  # Cache con un Time-To-Live (TTL) di 600 secondi
async def a_get_secret_key(source_identifier: str) -> str:
    kv_settings = KeyVaultSettings()
    # Recupero la mappatura delle chiavi
    file_content = await a_get_blob_content_from_container(kv_settings.secret_map_container_name, kv_settings.secret_map_file_name)
    map = json.loads(file_content)

    # Creo il client del Key Vault
    kv_settings = KeyVaultSettings()
    credential = DefaultAzureCredential()
    kv_client = SecretClient(vault_url=kv_settings.url, credential=credential)

    # Cerco la chiave che ho ricevuto
    async with kv_client:
        async with credential:
            for item in map:
                if item["source_identifier"] == source_identifier:
                    keyvault_url = item["secret"]
                    # Estraggo il secret name dall'url
                    _, secret_name, version = extract_keyvault_info(keyvault_url)
                    # Recupero il secret
                    secret = await kv_client.get_secret(secret_name, version)
                    
                    if not secret or not secret.value:
                        raise ValueError(f"An empty secret found for {source_identifier}")
                    
                    return secret.value

    raise ValueError(f"'caller-service' {source_identifier} not yet configured in configuration file. Please refer to GenAiAsPlatform administrators.")


def extract_keyvault_info(input_string: str) -> Tuple[str, str, str]:
    pattern = r"https:\/\/(?P<keyvault_name>[A-z0-9-]+)\.vault.azure.net\/secrets\/(?P<secret_name>[A-z0-9-]+)(\/(?P<version>[A-z0-9]+))?"
    match = re.search(pattern, input_string)
    
    if match:
        keyvault_name = match.group('keyvault_name')
        secret_name = match.group('secret_name')
        # opzionale la version
        version = match.group('version') if match.group('version') else None  
        return keyvault_name, secret_name, version # type: ignore
    else:
        raise ValueError("Error extracting data from keyvault url")