import json
from constants import llm as llm_const

class PromptEditorRequest:
    def __init__(self, 
                 id: str,
                 version: str,
                 type: llm_const):
        self.id = id
        self.version = version
        self.type = type

    def toJSON(self):
        return json.dumps(self,
                          default=lambda o: o.__dict__,
                          indent=4)