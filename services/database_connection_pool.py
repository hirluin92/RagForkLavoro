import aioodbc
from utils.settings import get_mssql_settings

settings = get_mssql_settings()

class DatabaseConnectionPool:
    _instance = None
    _pool = None
    _dsn = settings.connection_string

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnectionPool, cls).__new__(cls)
        return cls._instance

    async def get_pool(self):
        if self._pool is None:
            self._pool = await aioodbc.create_pool(dsn=self._dsn)
        return self._pool