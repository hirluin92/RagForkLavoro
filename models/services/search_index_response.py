from dataclasses import dataclass


@dataclass
class Value:
    search_score: float
    search_rerankerScore: float
    chunk_id: str
    chunk_text: str
    filename: str
    tags: list[str]

    @staticmethod
    def from_dict(obj: any) -> 'Value':
        _search_score = float(obj.get("@search.score"))
        _search_rerankerScore = float(obj.get("@search.rerankerScore", -1))
        _chunk_id = str(obj.get("chunk_id"))
        _chunk_text = str(obj.get("chunk_text"))
        _filename = str(obj.get("filename"))
        _tags = [str(y) for y in obj.get("tags")]
        return Value(_search_score,
                    _search_rerankerScore,
                    _chunk_id,
                    _chunk_text,
                    _filename,
                    _tags)
    
@dataclass
class SearchIndexResponse():
    data_context: str
    data_count: int
    value: list[Value]

    @staticmethod
    def from_dict(obj: any) -> 'SearchIndexResponse':
        _data_context = str(obj.get("@odata.context"))
        _data_count = int(obj.get("@odata.count", 0))
        _value = [Value.from_dict(y) for y in obj.get("value", [])]
        return SearchIndexResponse(_data_context,
                                   _data_count,
                                   _value)