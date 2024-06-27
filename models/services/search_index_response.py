from dataclasses import dataclass

@dataclass
class SearchAnswer:
    key: str
    text: str
    highlights: str
    score: float

    @staticmethod
    def from_dict(obj: any) -> 'SearchAnswer':
        _key = str(obj.get("key"))
        _text = str(obj.get("text"))
        _highlights = str(obj.get("highlights"))
        _score = float(obj.get("score"))
        return SearchAnswer(_key, _text, _highlights, _score)
    
@dataclass
class SearchCaption:
    text: str
    highlights: str

    @staticmethod
    def from_dict(obj: any) -> 'SearchCaption':
        _text = str(obj.get("text"))
        _highlights = str(obj.get("highlights"))
        return SearchCaption(_text, _highlights)

@dataclass
class Value:
    search_score: float
    search_rerankerScore: float
    search_captions: list[SearchCaption]
    chunk_id: str
    chunk_text: str
    filename: str
    tags: list[str]

    @staticmethod
    def from_dict(obj: any) -> 'Value':
        _search_score = float(obj.get("@search.score"))
        _search_rerankerScore = float(obj.get("@search.rerankerScore"))
        _search_captions = [SearchCaption.from_dict(y) for y in obj.get("@search.captions", [])]
        _chunk_id = str(obj.get("chunk_id"))
        _chunk_text = str(obj.get("chunk_text"))
        _filename = str(obj.get("filename"))
        _tags = [str(y) for y in obj.get("tags")]
        return Value(_search_score,
                    _search_rerankerScore,
                    _search_captions,
                    _chunk_id,
                    _chunk_text,
                    _filename,
                    _tags)
    
@dataclass
class SearchIndexResponse():
    data_context: str
    data_count: int
    search_answers: list[SearchAnswer]
    value: list[Value]

    @staticmethod
    def from_dict(obj: any) -> 'SearchIndexResponse':
        _data_context = str(obj.get("@odata.context"))
        _data_count = int(obj.get("@odata.count", 0))
        _search_answers = [SearchAnswer.from_dict(y) for y in obj.get("@search.answers", [])]
        _value = [Value.from_dict(y) for y in obj.get("value", [])]
        return SearchIndexResponse(_data_context,
                                   _data_count,
                                   _search_answers,
                                   _value)