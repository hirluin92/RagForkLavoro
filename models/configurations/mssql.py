from pydantic_settings import BaseSettings, SettingsConfigDict

class MsSqlSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='AZURE_SQL_')
    
    connection_string:str