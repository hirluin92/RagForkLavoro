from dataclasses import dataclass
from typing import List, Optional
import json
from typing import Any

@dataclass
class StatoDomanda:
    dataAggiornamento: str
    stato: str
    sottostato: str

@dataclass
class Domanda:
    numeroDomus: str
    progressivoIstanza: int
    nomePrestazione: str
    dataPresentazione: str
    numeroProtocollo: str
    statoDomanda: StatoDomanda
    sede: str
    modalitaVisualizzazione: str
    codiceProdottoDomus: str
    codiceProceduraDomus: int
    codiceStatoDomandaDomus: Optional[str]
    dettagliDomanda: Optional[str]

@dataclass
class DomusFormApplicationsByFiscalCodeResponse:
    messaggioErrore: Optional[str]
    errore: bool
    numeroPagine: Optional[int]
    numeroTotaleElementi: Optional[int]
    listaDomande: List[Domanda]

    # # Funzione per deserializzare il JSON in oggetti dataclass
    # def from_dict(self, data_class, data):
    #     if isinstance(data, list):
    #         return [self.from_dict(data_class, item) for item in data]
    #     if isinstance(data, dict):
    #         fieldtypes = {f.name: f.type for f in data_class.__dataclass_fields__.values()}
    #         return data_class(**{f: self.from_dict(fieldtypes[f], data[f]) for f in data})
    #     return data
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'DomusFormApplicationsByFiscalCodeResponse':
        return cls(**data)