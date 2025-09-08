from typing import Optional
from models.configurations.llm_consumer import LLMConsumer
from utils.secret_key_manager import a_get_secret_key
from utils.settings import get_access_control_settings, get_openai_settings
import azure.functions as func


async def handle_access_control(
    req: func.HttpRequest, logger
) -> LLMConsumer:
    ac_settings = get_access_control_settings()
    settings = get_openai_settings()
    caller_service = req.headers.get("caller-service")
    completion_key: Optional[str] = None

    if not caller_service:
        if ac_settings.enable_access_control:
            logger.info("Invocation from customer: {0} - setting default values".format("unknown"))
            completion_key = settings.completion_key
            caller_service = "default"
        else:
            raise ValueError("Missing 'caller-service' header")
    else:
        try:
            logger.info("Invocation from customer: {0}".format(caller_service))
            completion_key = await a_get_secret_key(settings.completion_key_storage_format.format(caller_service))
            if completion_key is None or completion_key == "":
                raise ValueError(
                    "Missing completion key in configuration settings for caller service: {0}".format(
                        caller_service
                    )
                )
        except ValueError as ve:
            raise ve

    logger.track_event("CallerServiceHeader", {"caller-service": caller_service})
    return LLMConsumer(name=caller_service, completion_key=completion_key)
