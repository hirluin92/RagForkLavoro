import ssl
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class DomusApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='DOMUS_')
    
    ibm_client_id_name: str
    ibm_client_secret_name: str
    base_url: str
    relative_url: str
    get_form_applications_by_fiscal_code_url: str
    get_form_application_details_url: str
    ssl_context_check_hostname: bool = False
    ssl_context_verify_mode: int = 0