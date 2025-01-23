class DomusFormApplicationDetailsRequest:
    def __init__(self, 
                 numero_domus: str,
                 progressivo_istanza: int,
                 token: str,
                 language: str = "it"):
        self.numero_domus = numero_domus
        self.token = token
        self.language = language
        self.progressivo_istanza = progressivo_istanza