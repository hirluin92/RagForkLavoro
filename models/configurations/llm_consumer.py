from typing import Optional


class LLMConsumer():
    completion_key: Optional[str] = None
    name: str

    def __init__(self, name: str, completion_key: Optional[str]):
        self.name = name
        self.completion_key = completion_key
