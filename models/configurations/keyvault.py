from pydantic_settings import BaseSettings, SettingsConfigDict

class KeyVaultSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='AZURE_KEY_VAULT_')
    
    secret_map_container_name: str  # Nome del container per il file delle mappature
    secret_map_file_name: str  # Nome del file delle mappature

    # Credenziali per l'accesso al Key Vault
    url: str  # URL del Key Vault
    # tenant_id: str
    # client_id: str
    # client_secret: str
    def __init__(self, **kwargs):
        super().__init__(**kwargs)