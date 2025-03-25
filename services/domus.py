import json
from logging import Logger
from aiohttp import ClientSession
from tenacity import retry, stop_after_attempt, wait_exponential
from constants import event_types
from models.apis.domus_form_application_details_request import DomusFormApplicationDetailsRequest
from models.apis.domus_form_application_details_response import DomusFormApplicationDetailsResponse
from models.apis.domus_form_applications_by_fiscal_code_request import DomusFormApplicationsByFiscalCodeRequest
from models.apis.domus_form_applications_by_fiscal_code_response import  DomusFormApplicationsByFiscalCodeResponse
from constants import misc as misc_const
from models.configurations.domus import DomusApiSettings
import ssl
from utils.tenacity import retry_if_http_error, wait_for_retry_after_header

@retry(
    retry=retry_if_http_error(),
    wait=wait_for_retry_after_header(fallback=wait_exponential(multiplier=1, min=4, max=10)),
    stop=stop_after_attempt(3),
    reraise=True
)
async def a_get_form_applications_by_fiscal_code(request: DomusFormApplicationsByFiscalCodeRequest,
                                          session: ClientSession,
                                          logger: Logger) -> DomusFormApplicationsByFiscalCodeResponse:

        settings = DomusApiSettings()
        endpoint = f"{settings.base_url}/{settings.relative_url}/{settings.get_form_applications_by_fiscal_code_url}?codiceFiscale={request.user_fiscal_code}&lingua={request.language.upper()}"

        ssl_context = None
        
        if settings.ssl_context_enable_custom:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = settings.ssl_context_check_hostname
                ssl_context.verify_mode = settings.ssl_context_verify_mode
        
        logger.track_event(event_types.domus_api_form_applications_by_fiscal_code_request, {"request_endpoint": endpoint})
        
        headers = {misc_const.HTTP_HEADER_X_IBM_CLIENT_ID_NAME: settings.ibm_client_id,
                misc_const.HTTP_HEADER_X_IBM_CLIENT_SECRET_NAME: settings.ibm_client_secret,
                misc_const.HTTP_HEADER_AUTHORIZATION: f"{misc_const.HTTP_HEADER_BEARER_NAME} {request.token}"
                }
    
        async with session.post(endpoint,
                        headers=headers,
                        ssl=ssl_context if ssl_context is not None else None) as result:
                result_json = await result.json()
                result_obj = DomusFormApplicationsByFiscalCodeResponse.model_validate(result_json)

                result_obj.listaDomande = [domanda for domanda in result_obj.listaDomande if domanda.codiceProceduraDomus == request.form_application_code]

                logger.track_event(event_types.domus_api_form_applications_by_fiscal_code_response, {"response": "OK"})
                return result_obj
    
@retry(
    retry=retry_if_http_error(),
    wait=wait_for_retry_after_header(fallback=wait_exponential(multiplier=1, min=4, max=10)),
    stop=stop_after_attempt(3),
    reraise=True
)
async def a_get_form_application_details(request: DomusFormApplicationDetailsRequest,
                                          session: ClientSession,
                                          logger: Logger,) -> DomusFormApplicationDetailsResponse:
        settings = DomusApiSettings()
        endpoint = f"{settings.base_url}/{settings.relative_url}/{settings.get_form_application_details_url}?numeroDomus={request.domus_number}&lingua={request.language.upper()}&progressivoIstanza={request.progressivo_istanza}"

        ssl_context = None

        if settings.ssl_context_enable_custom:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = settings.ssl_context_check_hostname
                ssl_context.verify_mode = settings.ssl_context_verify_mode

        logger.track_event(event_types.domus_api_form_application_details_request, {"request_endpoint": endpoint})

        headers = {misc_const.HTTP_HEADER_X_IBM_CLIENT_ID_NAME: settings.ibm_client_id,
                misc_const.HTTP_HEADER_X_IBM_CLIENT_SECRET_NAME: settings.ibm_client_secret,
                misc_const.HTTP_HEADER_AUTHORIZATION: f"{misc_const.HTTP_HEADER_BEARER_NAME} {request.token}"}

        async with session.post(endpoint,
                                headers=headers,
                                ssl=ssl_context if ssl_context is not None else None) as result:
                result_json = await result.json()
                result_obj = DomusFormApplicationDetailsResponse.model_validate(result_json)

                logger.track_event(event_types.domus_api_form_application_details__response, {"response": "OK"})
                return result_obj