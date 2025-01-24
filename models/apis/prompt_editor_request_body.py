from dataclasses import dataclass
import json
from constants import llm as llm_const

@dataclass
class PromptEditorRequest:
    def __init__(self, 
                 id: str,
                 version: str,
                 label: llm_const):
        self.id = id
        self.version = version
        self.label = label

    def toJSON(self):
        return json.dumps(self,
                          default=lambda o: o.__dict__,
                          indent=4)
    
    def to_dict(self):
        return {
            'id': self.id,
            'version': self.version,
            'label': self.label
        }
