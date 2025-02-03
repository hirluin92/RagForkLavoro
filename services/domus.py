from logging import Logger
from aiohttp import ClientSession
from constants import event_types
from models.apis.domus_form_application_details_request import DomusFormApplicationDetailsRequest
from models.apis.domus_form_application_details_response import DomusFormAapplicationDetailsResponse
from models.apis.domus_form_applications_by_fiscal_code_request import DomusFormApplicationsByFiscalCodeRequest
from models.apis.domus_form_applications_by_fiscal_code_response import  DomusFormApplicationsByFiscalCodeResponse
from constants import misc as misc_const
from models.configurations.domus import DomusApiSettings
import ssl


async def a_get_form_applications_by_fiscal_code(request: DomusFormApplicationsByFiscalCodeRequest,
                                          session: ClientSession,
                                          logger: Logger) -> DomusFormApplicationsByFiscalCodeResponse:

        settings = DomusApiSettings()
        endpoint = f"{settings.base_url}/{settings.relative_url}/{settings.get_form_applications_by_fiscal_code_url}?codiceFiscale={request.user_fiscal_code}&lingua={request.language.upper()}"

        # Crea un contesto SSL personalizzato
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        logger.track_event(event_types.domus_api_form_applications_by_fiscal_code_request, {"request_endpoint": endpoint})
        
        headers = {misc_const.HTTP_HEADER_X_IBM_CLIENT_ID_NAME: settings.ibm_client_id_name,
                misc_const.HTTP_HEADER_X_IBM_CLIENT_SECRET_NAME: settings.ibm_client_secret_name,
                misc_const.HTTP_HEADER_AUTHORIZATION: f"{misc_const.HTTP_HEADER_BEARER_NAME} {request.token}"
                }
    
        async with session.post(endpoint,
                        headers=headers,
                        ssl = ssl_context) as result:
                result_json = await result.json()
                result_obj = DomusFormApplicationsByFiscalCodeResponse.model_validate(result_json)

                # AGGIUNGERE FILTER BY TAGS
                # result_obj.listaDomande = [domanda for domanda in result_obj.listaDomande if domanda.codiceProceduraDomus == request.form_application_code 
                #                     and (domanda.statoDomanda.stato is None or domanda.statoDomanda.stato == request.form_application_status)]
                result_obj.listaDomande = [domanda for domanda in result_obj.listaDomande if domanda.codiceProceduraDomus == request.form_application_code]

                logger.track_event(event_types.domus_api_form_applications_by_fiscal_code_response, {"response": "OK"})
                return result_obj
    
async def a_get_form_application_details(request: DomusFormApplicationDetailsRequest,
                                          session: ClientSession,
                                          logger: Logger,) -> DomusFormAapplicationDetailsResponse:

        settings = DomusApiSettings()
        endpoint = f"{settings.base_url}/{settings.relative_url}/{settings.get_form_application_details_url}?numeroDomus={request.domus_number}&lingua={request.language.upper()}&progressivoIstanza={request.progressivo_istanza}"

        # Crea un contesto SSL personalizzato
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        logger.track_event(event_types.domus_api_form_application_details_request, {"request_endpoint": endpoint})

        headers = {misc_const.HTTP_HEADER_X_IBM_CLIENT_ID_NAME: settings.ibm_client_id_name,
                misc_const.HTTP_HEADER_X_IBM_CLIENT_SECRET_NAME: settings.ibm_client_secret_name,
                misc_const.HTTP_HEADER_AUTHORIZATION: f"{misc_const.HTTP_HEADER_BEARER_NAME} {request.token}"}

        async with session.post(endpoint,
                                headers=headers,
                                ssl = ssl_context) as result:
                result_json = await result.json()
                result_obj = DomusFormAapplicationDetailsResponse.model_validate(result_json)

                logger.track_event(event_types.domus_api_form_application_details__response, {"response": "OK"})
                return result_obj