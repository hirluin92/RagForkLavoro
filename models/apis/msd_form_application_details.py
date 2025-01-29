from typing import List, Optional
from pydantic import BaseModel

class ListaContenuti(BaseModel):
    labelContenuto: Optional[str]
    descrizioneContenuto: Optional[str]
    ordineContenuto: Optional[int]

class ListaStati(BaseModel):
    step: Optional[int]
    corrente: Optional[bool]
    completato: Optional[bool]
    ultimoStep: Optional[bool]
    dataAggiornamento: Optional[int]
    stato: Optional[str]
    sottostato: Optional[str]
    tooltip: Optional[str]
    scope: Optional[str]
    listaContenuti: Optional[List[ListaContenuti]]

class AltriDati(BaseModel):
    nome: Optional[str]
    valore: Optional[str]
    
class Adempimenti(BaseModel):
    titolo: Optional[str]
    descrizione: Optional[str]
    dataAdempimento: Optional[int]

class DomusFormAapplicationDetailsResponse(BaseModel):
    prodotto: Optional[str]
    nomeCompleto: Optional[str]
    dataPresentazione: Optional[int]
    numeroDomus: Optional[str]
    progressivoIstanza: Optional[int]
    numeroProtocollo: Optional[str]
    siglaPatronato: Optional[str]
    modalitaPresentazione: Optional[str]
    listaStati: Optional[List[ListaStati]]
    adempimenti: Optional[List[str]]
    codiceFiscaleTitolareDomanda: Optional[str]
    scopeStatoCorrente: Optional[str]
    codiceProdottoDomus: Optional[str]
    codiceProceduraDomus: Optional[int]
    codiceStatoDomandaDomus: Optional[str]
    listaDocumentiDomanda: Optional[List[str]]
    codiceProdotto: Optional[str]
    codiceSottoprodotto: Optional[str]
    errore: Optional[bool]
    messaggioErrore: Optional[str]
    codiceErrore: Optional[str]