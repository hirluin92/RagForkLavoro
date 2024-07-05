from pydantic_settings import BaseSettings, SettingsConfigDict

class PromptSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='PROMPT_')
    
    answer_generation_markdown_enabled: bool