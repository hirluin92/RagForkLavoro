class CLog:
    def __init__(self, ret_code, err_desc = None):
        self.ret_code = ret_code
        self.err_desc = err_desc
    ret_code: int
    err_desc: str