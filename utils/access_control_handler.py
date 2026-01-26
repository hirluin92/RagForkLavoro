from typing import Optional
from models.configurations.llm_consumer import LLMConsumer
from utils.db_config import a_get_complete_config, DeploymentNotFoundError, DatabaseConnectionError, IncompleteConfigError, SecretRetrievalError, InvalidSecretUrlError
from utils.settings import get_access_control_settings, get_openai_settings
import azure.functions as func


async def handle_access_control(
    req: func.HttpRequest, logger, model_name: Optional[str] = None
) -> LLMConsumer:
    """
    Gestisce access control e recupera configurazione deployment.
    
    Args:
        req: HttpRequest con header 'caller-service'
        logger: Logger per tracciamento
        model_name: Nome deployment/modello (obbligatorio se access control abilitato)
    
    Returns:
        LLMConsumer con configurazione completa
        
    Raises:
        ValueError: se manca caller-service o model_name quando richiesto
        DeploymentNotFoundError: deployment non trovato in SQL
        DatabaseConnectionError: errore connessione SQL
        SecretRetrievalError: errore recupero secret da Key Vault
    """
    ac_settings = get_access_control_settings()
    settings = get_openai_settings()
    caller_service = req.headers.get("caller-service")
    completion_key: Optional[str] = None
    deployment_model: Optional[str] = None
    api_version: Optional[str] = None

    if not caller_service:
        if not ac_settings.enable_access_control:
            logger.info("Invocation from customer: {0} - setting default values".format("unknown"))
            completion_key = settings.completion_key
            caller_service = "default"
        else:
            raise ValueError("Missing 'caller-service' header")
    else:
        try:
            logger.info("Invocation from customer: {0}".format(caller_service))
            
            # Verifica che model_name sia fornito
            if not model_name:
                raise ValueError(
                    "Missing 'model_name' in request body. Required for deployment configuration."
                )
            
            # Usa nuova funzione a_get_complete_config con chiave composta
            source_identifier = settings.completion_key_storage_format.format(caller_service)
            config = await a_get_complete_config(
                source_identifier=source_identifier,
                model_name=model_name
            )
            
            completion_key = config["api_key"]
            deployment_model = config.get("deployment")
            api_version = config.get("api_version")
            
            if completion_key is None or completion_key == "":
                raise ValueError(
                    "Missing completion key in configuration settings for caller service: {0}".format(
                        caller_service
                    )
                )
        except (DeploymentNotFoundError, DatabaseConnectionError, IncompleteConfigError, 
                SecretRetrievalError, InvalidSecretUrlError) as e:
            # Rilancia le custom exceptions così possono essere gestite nell'handler
            raise e
        except ValueError as ve:
            raise ve

    logger.track_event("CallerServiceHeader", {"caller-service": caller_service})
    return LLMConsumer(
        name=caller_service, 
        completion_key=completion_key,
        deployment_model=deployment_model,
        api_version=api_version
    )
