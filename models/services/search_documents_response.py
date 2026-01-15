from dataclasses import dataclass

@dataclass
class SearchDocument:
    chunk_id: str
    filename: str
    blob_name: str
    tags: list[str]

    @staticmethod
    def from_dict(obj: any) -> 'SearchDocument':
        _chunk_id = str(obj.get("chunk_id"))
        _filename = str(obj.get("filename"))
        _blob_name = str(obj.get("blob_name", ""))
        _tags = [str(y) for y in obj.get("tags")]

        return SearchDocument(_chunk_id, _filename, _blob_name, _tags)
    

@dataclass
class SearchDocumentsResponse:
    value: list[SearchDocument]
    nextPage: bool
    count: int

    @staticmethod
    def from_dict(obj: any) -> 'SearchDocumentsResponse':
        _value = [SearchDocument.from_dict(y) for y in obj.get("value", [])]
        _nextPageLink = str(obj.get("@odata.nextLink", ""))
        _count = int(obj.get("@odata.count", 0))

        return SearchDocumentsResponse(_value, len(_nextPageLink)>0, _count)
