from dataclasses import dataclass
import json


@dataclass
class LlmContextContent:
    chunk: str
    reference: int
    score: float

    def toJSON(self):
        return json.dumps(self,
                          default=lambda o: o.__dict__,
                          indent=4)