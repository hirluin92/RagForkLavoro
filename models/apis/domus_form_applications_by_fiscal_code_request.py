class DomusFormApplicationsByFiscalCodeRequest:
    
    def __init__(self, 
                 user_fiscal_code: str,
                 token: int,
                 form_application_code: int = None,
                 form_application_status: str = None,
                 language: str = "IT"):
        self.user_fiscal_code = user_fiscal_code
        self.token = token
        self.form_application_code = form_application_code
        self.language = language
        self.form_application_status = form_application_status
        
    