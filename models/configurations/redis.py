from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='REDIS_')

    host: str
    password: str
    port: Optional[int] = 6380
    expiration_seconds: Optional[int] = 180
    ssl:Optional[bool]=True
