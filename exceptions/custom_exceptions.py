from models.configurations.clog import CLog

class CustomPromptParameterError(Exception):
    def __init__(self, message, error_code):            
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        
class MonitorFormApplicationException(Exception):
    clog: CLog
    error_code: int
    error_message: str
    
    def __init__(self, message, error_code, clog):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.clog = clog
