import json
from typing import Any, Optional
from typing import Optional

class PromptMessage:
    def __init__(self,
                 role: str,
                 content: str):
        self.role = role
        self.content = content
 
 
class OpenAIModelParameters:
    def __init__(self,
                 top_p: float,
                 temperature: float,
                 max_length: int,
                 stop_sequence: str):
        self.top_p = top_p
        self.temperature = temperature
        self.max_length = max_length
        self.stop_sequence = stop_sequence
 
 
class PromptEditorResponseBody:
    def __init__(self,
                 id: str,
                 label: Optional[str],
                 version: str,
                 llm_model: str,
                 prompt: list[PromptMessage],
                 parameters: list[str],
                 model_parameters: Any,
                 validation_messages: list[str]):
        self.id = id
        self.label = label
        self.version = version
        self.llm_model = llm_model
        self.prompt = prompt
        self.parameters = parameters
        self.model_parameters = model_parameters
        self.validation_messages = validation_messages
        
 
    def toJSON(self):
        return json.dumps(self,
                          default=lambda o: o.__dict__,
                          indent=4)
 
    @staticmethod
    def from_dict(data: dict) -> 'PromptEditorResponseBody':
        model_params = OpenAIModelParameters(**data['model_parameters'])      
        prompts = [PromptMessage(**mex) for mex in data['prompt']]
        return PromptEditorResponseBody(
            id=data['id'],
            label=data['label'],
            version=data['version'],
            llm_model=data['llm_model'],
            prompt=prompts,
            parameters=data['parameters'],
            model_parameters=model_params,
            validation_messages=data['validation_messages']
        )