from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class CLogSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='CLOG_')
    
    clog_msd_elencodomande: str
    clog_msd_dettagliodomande: str

class CLogParams(BaseModel):
    cf: str = None
    prestazione: str = None
    num_prot: str = None
    num_domus: str = None

class CLog(BaseModel):
    ret_code: int
    err_desc: str = None
    id_event: str = None
    params: CLogParams = None