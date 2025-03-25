from typing import Optional
from redis import Redis

from models.configurations.redis import RedisSettings

settings = RedisSettings()

_redis_instance = Redis(host=settings.host, password=settings.password,
                        port=settings.port, decode_responses=True, ssl=True)


def get_from_redis(key: str) -> Optional[str]:
    return _redis_instance.get(key)


def set_to_redis(key: str, value: str):
    _redis_instance.set(key, value, ex=settings.expiration_seconds)
