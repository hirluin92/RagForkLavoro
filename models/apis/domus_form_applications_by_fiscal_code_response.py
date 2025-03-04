from typing import Optional
from pydantic import BaseModel
from models.configurations.clog import CLog

class StatoDomanda(BaseModel):
    dataAggiornamento: Optional[str]
    stato: Optional[str]
    sottostato: Optional[str]

class Domanda(BaseModel):
    numeroDomus: Optional[str]
    progressivoIstanza: Optional[int]
    nomePrestazione: Optional[str]
    dataPresentazione: Optional[str]
    numeroProtocollo: Optional[str]
    statoDomanda: Optional[StatoDomanda]
    sede: Optional[str]
    modalitaVisualizzazione: Optional[str]
    codiceProdottoDomus: Optional[str]
    codiceProceduraDomus: Optional[int]
    codiceStatoDomandaDomus: Optional[str]
    dettagliDomanda: Optional[str]

class DomusFormApplicationsByFiscalCodeResponse(BaseModel):
    messaggioErrore: Optional[str]
    errore: Optional[bool]
    numeroPagine: Optional[int]
    numeroTotaleElementi: Optional[int]
    listaDomande: Optional[list[Domanda]]
    clog: Optional[CLog] = None