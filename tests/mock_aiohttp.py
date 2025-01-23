import json

class MockClientResponse:
    def __init__(self, data, status):
        self._data = data
        self.status = status
    
    async def json(self):
        return self._data

    async def raise_for_status(self):
        pass

    async def text(self):
        return json.dumps(self._data, ensure_ascii=False).encode('utf-8')

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def __aenter__(self):
        return self

class MockClientSession:
    def __init__(self, response: MockClientResponse):
        self._response = response
    def get(self,*args, **kwargs):
        return self._response
    def post(self,*args, **kwargs):
        return self._response
    
    async def __aexit__(self, exc_type, exc, tb):
        pass
    async def __aenter__(self):
        return self

