import json
from typing import Any, Optional
from typing import Optional


class PromptMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


class OpenAIModelParameters:
    def __init__(self, temperature: float, top_p: float, max_length: int, stop_sequence: str):
        self.temperature = temperature
        self.top_p = top_p
        self.max_length = max_length
        self.stop_sequence = stop_sequence


class PromptEditorResponseBody:
    def __init__(
        self,
        id: str,
        label: Optional[str],
        version: str,
        llm_model: str,
        prompt: list[PromptMessage],
        parameters: list[str],
        model_parameters: Any,
        validation_messages: list[str],
    ):
        self.id = id
        self.label = label
        self.version = version
        self.llm_model = llm_model
        self.prompt = prompt
        self.parameters = parameters
        self.model_parameters = model_parameters
        self.validation_messages = validation_messages

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

    @staticmethod
    def from_dict(data: dict) -> "PromptEditorResponseBody":
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            # Se 'data' è una lista, non è vuota, e il suo primo elemento è un dizionario,
            # allora procedi come previsto.
            data_dictionary = data[0]
        else:
            data_dictionary = data

        model_params = OpenAIModelParameters(**data_dictionary["model_parameters"])
        prompts = [PromptMessage(**mex) for mex in data_dictionary["prompt"]]
        return PromptEditorResponseBody(
            id=data_dictionary["id"],
            label=data_dictionary["label"],
            version=data_dictionary["version"],
            llm_model=data_dictionary["llm_model"],
            prompt=prompts,
            parameters=data_dictionary["parameters"],
            model_parameters=model_params,
            validation_messages=data_dictionary["validation_messages"],
        )
