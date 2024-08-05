from pydantic import BaseModel

class DataFromAzAISearch(BaseModel):
    fileUrl: str
    fileSasToken: str

class ValueFromAzAISearch(BaseModel):
    recordId: str
    data: DataFromAzAISearch

class ChunkingEmptyRowsRequestBody(BaseModel):
    values: list[ValueFromAzAISearch]