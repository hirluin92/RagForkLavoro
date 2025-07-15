

class LLMConsumer():
    completion_key: str
    name: str

    def __init__(self, name: str, completion_key: str):
        self.name = name
        self.completion_key = completion_key