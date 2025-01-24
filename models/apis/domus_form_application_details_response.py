from dataclasses import dataclass
from typing import List, Optional
from typing import Any

@dataclass
class ListaContenuti:
    labelContenuto: Optional[str]
    descrizioneContenuto: Optional[str]
    ordineContenuto: Optional[int]

@dataclass
class ListaStati:
    step: int
    corrente: bool
    completato: bool
    ultimoStep: bool
    dataAggiornamento: Optional[int]
    stato: str
    sottostato: str
    tooltip: str
    scope: Optional[str]
    listaContenuti: List[ListaContenuti]

@dataclass
class AltriDati:
    nome: str
    valore: Optional[str]
    
@dataclass
class Adempimenti:
    titolo: Optional[str]
    descrizione: Optional[str]
    dataAdempimento: Optional[int]

@dataclass
class DomusFormAapplicationDetailsResponse:
    prodotto: str
    nomeCompleto: str
    dataPresentazione: int
    numeroDomus: str
    progressivoIstanza: int
    numeroProtocollo: str
    siglaPatronato: Optional[str]
    modalitaPresentazione: str
    listaStati: List[ListaStati]
    adempimenti: List[str]
    codiceFiscaleTitolareDomanda: str
    scopeStatoCorrente: str
    codiceProdottoDomus: str
    codiceProceduraDomus: int
    codiceStatoDomandaDomus: str
    listaDocumentiDomanda: List[str]
    codiceProdotto: str
    codiceSottoprodotto: Optional[str]
    errore: Optional[bool]
    messaggioErrore: Optional[str]
    codiceErrore: Optional[str]
    
    @classmethod
    def custom_decoder(dct):
        if 'listaStati' in dct:
            dct['listaStati'] = ListaStati(**dct['listaStati'])
            
        if 'altriDati' in dct:
            dct['altriDati'] = AltriDati(**dct['altriDati'])
            
        if 'listaContenuti' in dct:
            dct['listaContenuti'] = ListaContenuti(**dct['altrlistaContenutiiDati'])
        return dct
        
        
    def from_dict(cls, data: dict[str, Any]) -> 'DomusFormAapplicationDetailsResponse':
        return cls(**data)