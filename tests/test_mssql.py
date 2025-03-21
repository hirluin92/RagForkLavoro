# test_services_mssql.py

import pytest
import asyncio
from types import SimpleNamespace

# ---------------------------------------
# Fake classes per simulare il comportamento di aioodbc
# ---------------------------------------


class FakePoolContextManager:
    """Simula il context manager restituito da create_pool."""

    def __init__(self, fake_cursor):
        self.fake_cursor = fake_cursor

    async def __aenter__(self):
        return FakePool(self.fake_cursor)

    async def __aexit__(self, exc_type, exc, tb):
        pass


class FakePool:
    """Simula il pool (il quale ha il metodo acquire())."""

    def __init__(self, fake_cursor):
        self.fake_cursor = fake_cursor

    def acquire(self):
        return FakeConnectionContextManager(self.fake_cursor)


class FakeConnectionContextManager:
    """Simula il context manager restituito dal metodo acquire()."""

    def __init__(self, fake_cursor):
        self.fake_cursor = fake_cursor

    async def __aenter__(self):
        return FakeConnection(self.fake_cursor)

    async def __aexit__(self, exc_type, exc, tb):
        pass


class FakeConnection:
    """Simula la connessione (il quale ha il metodo cursor())."""

    def __init__(self, fake_cursor):
        self.fake_cursor = fake_cursor

    def cursor(self):
        return FakeCursorContextManager(self.fake_cursor)


class FakeCursorContextManager:
    """Simula il context manager per il cursore."""

    def __init__(self, fake_cursor):
        self.fake_cursor = fake_cursor

    async def __aenter__(self):
        return self.fake_cursor

    async def __aexit__(self, exc_type, exc, tb):
        pass


class FakeCursor:
    """
    Fake del cursore usato per:
      - eseguire le query (il metodo execute)
      - simulare il fetchall() (per a_get_tags_by_tag_names e a_check_status_tag_for_mst)
      - oppure l'iterazione asincrona (per a_get_prompt_info)
    """

    def __init__(self, fetchall_return=None, iter_records=None):
        self.fetchall_return = fetchall_return
        self.iter_records = iter_records if iter_records is not None else []
        self.executed_sql = None
        self.executed_params = None

    async def execute(self, sql, params=None):
        self.executed_sql = sql
        self.executed_params = params
        
    async def execute(self, sql, params=None, params2=None):
        self.executed_sql = sql
        self.executed_params = params
        self.executed_params2 = params2

    async def fetchall(self):
        return self.fetchall_return or []

    def __aiter__(self):
        self._iter = iter(self.iter_records)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration

# ---------------------------------------
# Fake record classes per simulare le righe ritornate dal database
# ---------------------------------------


class FakeRecord:
    """Record fittizio per a_get_tags_by_tag_names: deve avere attributi 'Name' e 'Description'."""

    def __init__(self, name, description):
        self.Name = name
        self.Description = description


class FakePromptRecord:
    """
    Record fittizio per a_get_prompt_info: deve avere attributi PromptId, PromptVersion e PromptType.
    """

    def __init__(self, prompt_id, prompt_version, prompt_type):
        self.PromptId = prompt_id
        self.PromptVersion = prompt_version
        self.PromptType = prompt_type

# ---------------------------------------
# Test per a_get_tags_by_tag_names
# ---------------------------------------


@pytest.mark.asyncio
async def test_a_get_tags_by_tag_names(monkeypatch):
    # Simula le impostazioni MSSQL
    dummy_settings = SimpleNamespace(
        connection_string="dummy_connection_string")
    monkeypatch.setattr("services.mssql.get_mssql_settings",
                        lambda: dummy_settings)

    # Prepara dei fake record da restituire tramite fetchall()
    fake_records = [
        FakeRecord("tag1", "desc1"),
        FakeRecord("tag2", "desc2")
    ]
    fake_cursor = FakeCursor(fetchall_return=fake_records)
    # Sostituisce create_pool con il nostro fake (verrà usato nel context manager)
    monkeypatch.setattr("services.mssql.create_pool", lambda dsn,
                        minsize: FakePoolContextManager(fake_cursor))

    # Creiamo un logger (qui viene usato solo per loggare)
    import logging
    logger = logging.getLogger("test_a_get_tags_by_tag_names")

    # Importa e chiama la funzione da testare
    from services.mssql import a_get_tags_by_tag_names
    result = await a_get_tags_by_tag_names(logger, ["tag1", "tag2"])

    # Importa la classe MsSqlTag per confrontare i risultati
    from models.services.mssql_tag import MsSqlTag
    # Crea il risultato atteso
    expected = [
        MsSqlTag("tag1", "desc1"),
        MsSqlTag("tag2", "desc2")
    ]

    # Verifica che il numero di elementi e i relativi attributi siano corretti.
    assert len(result) == len(expected)
    for res, exp in zip(result, expected):
        # Si confronta il __dict__ degli oggetti; adatta in base all'implementazione di MsSqlTag.
        assert res.__dict__ == exp.__dict__

# ---------------------------------------
# Test per a_get_prompt_info
# ---------------------------------------


@pytest.mark.asyncio
async def test_a_get_prompt_info(monkeypatch):
    dummy_settings = SimpleNamespace(
        connection_string="dummy_connection_string")
    monkeypatch.setattr("services.mssql.get_mssql_settings",
                        lambda: dummy_settings)

    # Prepara dei fake record con PromptId come stringa
    fake_records = [
        FakePromptRecord("101", "v1", "typeA"),
        FakePromptRecord("102", "v2", "typeB")
    ]
    fake_cursor = FakeCursor(iter_records=fake_records)
    monkeypatch.setattr("services.mssql.create_pool", lambda dsn,
                        minsize: FakePoolContextManager(fake_cursor))

    import logging
    logger = logging.getLogger("test_a_get_prompt_info")

    from services.mssql import a_get_prompt_info
    result = await a_get_prompt_info(logger, "some_tag", ["filter1", "filter2"], "OPENAI")

    assert len(result) == 2
    assert result[0].id == "101"
    assert result[0].version == "v1"
    assert result[0].type == "typeA"
    assert result[1].id == "102"
    assert result[1].version == "v2"
    assert result[1].type == "typeB"

    # Verifica che la query eseguita contenga la parte con "WITH FilteredRows"
    assert fake_cursor.executed_sql is not None
    assert "WITH FilteredRows AS" in fake_cursor.executed_sql
    # Nota: il parametro passato a execute è "some_tag" (poiché (tag_name) non crea una tupla)
    assert fake_cursor.executed_params == "some_tag"

# ---------------------------------------
# Test per a_check_status_tag_for_mst (caso in cui la query ritorna record, quindi True)
# ---------------------------------------


@pytest.mark.asyncio
async def test_a_check_status_tag_for_mst(monkeypatch):
    dummy_settings = SimpleNamespace(
        connection_string="dummy_connection_string")
    monkeypatch.setattr("services.mssql.get_mssql_settings",
                        lambda: dummy_settings)

    class FakeRecord:
        def __init__(self, id):
            self.IdMonitoringQuestion = id
    # Simula fetchall() che restituisce una lista non vuota (ad esempio [object()])
    fake_cursor = FakeCursor(fetchall_return=[FakeRecord(1)])
    monkeypatch.setattr("services.mssql.create_pool", lambda dsn,
                        minsize: FakePoolContextManager(fake_cursor))

    import logging
    logger = logging.getLogger("test_a_check_status_tag_for_mst_true")

    from services.mssql import a_check_status_tag_for_msd
    result = await a_check_status_tag_for_msd(logger, "tag_test")
    assert result == 1

