class DomusFormApplicationsByFiscalCodeRequest:
    def __init__(self, 
                 user_fiscal_code: str,
                 token: int,
                 language: str = "IT"):
        self.user_fiscal_code = user_fiscal_code
        self.token = token
        self.language = language