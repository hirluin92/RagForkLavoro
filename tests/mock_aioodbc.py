import json


class MockConnection:
    def __init__(self):
        pass

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def __aenter__(self):
        return self


class MockPool:
    def __init__(self):
        self._response = MockConnection()

    def acquire(self, *args, **kwargs):
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def __aenter__(self):
        return self


class MockAiodbc:
    def __init__(self, pool: MockPool):
        self._response = pool

    def create_pool(self, *args, **kwargs):
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def __aenter__(self):
        return self
