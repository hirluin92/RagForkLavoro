from pydantic_settings import BaseSettings, SettingsConfigDict

class BlobStorageSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='STORAGE_')
    
    account_key: str
    account_name: str
    bulk_split_files_container: str
    connection_string: str
    data_source_split_files_container: str
    prompt_files_container: str
    uploaded_files_container: str
    uploaded_split_files_container: str
  
