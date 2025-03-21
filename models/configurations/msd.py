from pydantic_settings import BaseSettings, SettingsConfigDict

class MsdSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='MSD_')
    
    no_form_app_def_answer: str = "Mi dispiace, ma dopo un'attenta verifica, purtroppo non sono riuscito a trovare alcuna domanda corrispondente ai tuoi criteri nei nostri sistemi"
    no_info_final_answer: str = "Grazie per aver utilizzato i nostri servizi! Se hai altre domande o hai bisogno di ulteriori informazioni, non esitare a chiedere. Sono qui a tua disposizione per aiutarti in qualsiasi momento"