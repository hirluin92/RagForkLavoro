from pydantic import BaseModel

class CLog(BaseModel):
    ret_code: int
    err_desc: str = None
