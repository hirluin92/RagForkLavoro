from typing import Optional


class LLMConsumer():
    completion_key: Optional[str] = None
    name: str
    deployment_model: Optional[str] = None
    api_version: Optional[str] = None

    def __init__(self, name: str, completion_key: Optional[str], 
                 deployment_model: Optional[str] = None,
                 api_version: Optional[str] = None):
        self.name = name
        self.completion_key = completion_key
        self.deployment_model = deployment_model
        self.api_version = api_version