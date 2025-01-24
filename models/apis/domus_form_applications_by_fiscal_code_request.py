class DomusFormApplicationsByFiscalCodeRequest:
    
    def __init__(self, 
                 user_fiscal_code: str,
                 token: int,
                 tag: str = None,
                 language: str = "IT"):
        self.user_fiscal_code = user_fiscal_code
        self.token = token
        self.tag = tag
        self.language = language
        
    