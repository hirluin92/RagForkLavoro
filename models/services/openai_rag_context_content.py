from dataclasses import dataclass
import json


@dataclass
class RagContextContent:
    chunk_id: str
    chunk: str
    reference: int
    filename: str
    caption: str
    score: float
    tags: str

    def toJSON(self):
        return json.dumps(self,
                          default=lambda o: o.__dict__,
                          indent=4)