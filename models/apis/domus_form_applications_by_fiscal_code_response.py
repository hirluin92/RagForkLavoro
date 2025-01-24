from dataclasses import dataclass
from dataclasses import dataclass, field

from typing import List, Optional, Any

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
    listaDomande: List[Domanda]= field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'DomusFormApplicationsByFiscalCodeResponse':
        # Funzione di decodifica personalizzata per gestire oggetti annidati
        def custom_decoder(dct):
            if 'statoDomanda' in dct:
                dct['statoDomanda'] = StatoDomanda(**dct['statoDomanda'])
            return dct
        
        # Deserializzare il JSON in un oggetto DomusFormApplicationsByFiscalCodeResponse
        # data['listaDomande'] = [Domanda(**custom_decoder(domanda)) for domanda in data['listaDomande']]
        # return cls(**data)
        
        # Deserializzare il JSON in un oggetto DomusFormApplicationsByFiscalCodeResponse con solo i parametri di interesse
        lista_domande = [
            Domanda(
                numeroDomus=domanda.get('numeroDomus', ''),
                progressivoIstanza=domanda.get('progressivoIstanza', 0),
                nomePrestazione=domanda.get('nomePrestazione', ''),
                dataPresentazione=domanda.get('dataPresentazione', ''),
                numeroProtocollo=domanda.get('numeroProtocollo', ''),
                statoDomanda=custom_decoder(domanda.get('statoDomanda', {})),
                sede=domanda.get('sede', ''),
                modalitaVisualizzazione=domanda.get('modalitaVisualizzazione', ''),
                codiceProdottoDomus=domanda.get('codiceProdottoDomus', ''),
                codiceProceduraDomus=domanda.get('codiceProceduraDomus', 0),
                codiceStatoDomandaDomus=domanda.get('codiceStatoDomandaDomus'),
                dettagliDomanda=domanda.get('dettagliDomanda')
            )
            for domanda in data.get('listaDomande', [])
        ]
        
        return cls(listaDomande=lista_domande)

    
    # @classmethod
    # def from_dict(cls, data: dict[str, Any]) -> 'DomusFormApplicationsByFiscalCodeResponse':
    #     return cls(**data)