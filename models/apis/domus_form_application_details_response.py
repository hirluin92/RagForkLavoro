from typing import List, Optional
from pydantic import BaseModel

class ListaContenuti(BaseModel):
    labelContenuto: Optional[str]= None
    descrizioneContenuto: Optional[str]= None
    ordineContenuto: Optional[int]= None

class ListaStati(BaseModel):
    step: Optional[int]= None
    corrente: Optional[bool]= None
    completato: Optional[bool]= None
    ultimoStep: Optional[bool]= None
    dataAggiornamento: Optional[int]= None
    stato: Optional[str]= None
    sottostato: Optional[str]= None
    tooltip: Optional[str]= None
    #scope: Optional[str]
    listaContenuti: Optional[List[ListaContenuti]]= None

#class AltriDati(BaseModel):
    #nome: Optional[str]
    #valore: Optional[str]
    
class Adempimenti(BaseModel):
    titolo: Optional[str]= None
    descrizione: Optional[str]= None
    dataAdempimento: Optional[int]= None

class DomusFormApplicationDetailsResponse(BaseModel):
    #prodotto: Optional[str]
    #nomeCompleto: Optional[str] = None
    #dataPresentazione: Optional[int]
    numeroDomus: Optional[str]
    #progressivoIstanza: Optional[int]
    numeroProtocollo: Optional[str]
    #siglaPatronato: Optional[str]
    #modalitaPresentazione: Optional[str]
    listaStati: Optional[List[ListaStati]]= None
    adempimenti: Optional[List[Adempimenti]]= None
    #codiceFiscaleTitolareDomanda: Optional[str]
    #scopeStatoCorrente: Optional[str]
    #codiceProdottoDomus: Optional[str]
    #codiceProceduraDomus: Optional[int]
    #codiceStatoDomandaDomus: Optional[str]
    #listaDocumentiDomanda: Optional[List[str]]
    #codiceProdotto: Optional[str]
    #codiceSottoprodotto: Optional[str]
    errore: Optional[bool]= None
    messaggioErrore: Optional[str]= None
    codiceErrore: Optional[str]= None