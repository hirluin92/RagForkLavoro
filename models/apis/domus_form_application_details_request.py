class DomusFormApplicationDetailsRequest:
    def __init__(self, 
                 domus_number: str,
                 progressivo_istanza: int,
                 token: str,
                 language: str = "it"):
        self.domus_number = domus_number
        self.token = token
        self.language = language
        self.progressivo_istanza = progressivo_istanza