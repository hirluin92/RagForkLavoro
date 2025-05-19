from typing import Optional,List
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


def make_key(prefix_type: str, convid: str, dettid: str = None) -> str:
    """
    Crea una chiave univoca per Redis combinando un prefisso statico con il nome fornito.

    :param prefix_type: Può essere "list" o "dett" per indicare il tipo di prefisso.
    :param name: Nome da concatenare alla chiave.
    :return: Chiave formattata per Redis.
    """
    prefix_map = {
        "list": "list_",
        "dett": "dett_"
    }

    prefix = prefix_map.get(prefix_type.lower())
    if not prefix:
        raise ValueError(f"Prefisso non valido: {prefix_type}. Usa 'list' o 'dett'.")

    return f"{prefix}{convid.lower()}{'_' + dettid if dettid else ''}"


def get_all_keys_by_conv_id(substring: str) -> List[str]:
    settings = RedisSettings()

    redis_instance = Redis(
        host=settings.host,
        password=settings.password,
        port=settings.port,
        decode_responses=True,
        ssl=True
    )

    substring_lower = substring.lower()

    # Prende tutte le chiavi Redis e filtra quelle che contengono la sottostringa (case-insensitive)
    keys = [
        key for key in redis_instance.scan_iter(match="*")
        if substring_lower in key.lower()
    ]

    return keys
