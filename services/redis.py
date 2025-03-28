from typing import Optional
from redis import Redis

from models.configurations.redis import RedisSettings

def get_from_redis(key: str) -> Optional[str]:
    settings = RedisSettings()

    redis_instance = Redis(host=settings.host, password=settings.password,
                            port=settings.port, decode_responses=True, ssl=True)

    return redis_instance.get(key.lower())


def set_to_redis(key: str, value: str):
    settings = RedisSettings()

    redis_instance = Redis(host=settings.host, password=settings.password,
                            port=settings.port, decode_responses=True, ssl=True)
    redis_instance.set(key.lower(), value, ex=settings.expiration_seconds)