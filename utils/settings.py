from functools import lru_cache
from models.configurations.cqa import CQASettings
from models.configurations.document_intelligence import DocumentIntelligenceSettings
from models.configurations.mistralai import MistralAISettings
from models.configurations.mssql import MsSqlSettings
from models.configurations.openai import OpenAISettings
from models.configurations.prompt import PromptSettings
from models.configurations.redis import RedisSettings
from models.configurations.search import SearchSettings
from models.configurations.storage import BlobStorageSettings
from models.configurations.access_control import AccessControlSettings

@lru_cache
def get_cqa_settings():
    return CQASettings()

@lru_cache
def get_document_intelligence_settings():
    return DocumentIntelligenceSettings()

@lru_cache
def get_mistralai_settings():
    return MistralAISettings()

@lru_cache
def get_mssql_settings():
    return MsSqlSettings()

@lru_cache
class OpenAISettingCached:
    def __init__(self):
        self.completion_key = None
        self.settings = OpenAISettings()

def get_openai_settings() -> OpenAISettings:
    return OpenAISettingCached().settings

def set_openai_settings(completion_key: str = None) -> OpenAISettings:
    """
    Restituisce le impostazioni di OpenAI, con la possibilità di sovrascrivere
    la 'completion_key' da un parametro.
    """
    __cached__: OpenAISettingCached = OpenAISettingCached()
    if completion_key is not None:
            __cached__.settings.completion_key = completion_key
    return __cached__.settings

@lru_cache
def get_search_settings():
    return SearchSettings()

@lru_cache
def get_storage_settings():
    return BlobStorageSettings()

@lru_cache
def get_prompt_settings():
    return PromptSettings()

@lru_cache
def get_redis_settings():
    return RedisSettings()

@lru_cache
def get_access_control_settings() -> AccessControlSettings:
    return AccessControlSettings()