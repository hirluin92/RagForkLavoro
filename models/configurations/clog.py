from typing import Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

class CLogSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='CLOG_')
    
    msd_elencodomande: str
    msd_dettagliodomande: str

class CLogParams(BaseModel):
    cf: Optional[str] = None
    prestazione: Optional[str] = None
    num_prot: Optional[str] = None
    num_domus: Optional[str] = None

class CLog(BaseModel):
    ret_code: Optional[int] = None
    err_desc: Optional[str] = None
    id_event: Optional[str] = None
    params: Optional[CLogParams] = None