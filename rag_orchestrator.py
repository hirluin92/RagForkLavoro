import aiohttp
import azure.functions as func
import json
from pydantic import ValidationError
from constants import event_types
from exceptions.custom_exceptions import CustomPromptParameterError
from logics.rag_orchestrator import a_get_query_response
from services.logging import LoggerBuilder
from utils.http_problem import Problem
from models.apis.rag_orchestrator_request import RagOrchestratorRequest
from utils.access_control_handler import handle_access_control
from utils.settings import (
    get_cqa_settings,
    get_mistralai_settings,
    get_mssql_settings,
    get_openai_settings,
    get_prompt_settings,
    get_search_settings,
    get_storage_settings,
)

bp = func.Blueprint()

@bp.route(route="rag", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
async def a_rag_orchestrator(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    with LoggerBuilder(__name__, context) as logger:
        logger.info("Rag orchestrator request")

        try:
            consumer = access_control = await handle_access_control(req, logger)

            get_cqa_settings()
            get_mistralai_settings()
            get_mssql_settings()
            get_prompt_settings()
            get_search_settings()
            get_storage_settings()
            get_openai_settings()
        
        except ValidationError as e:
            logger.exception("Invalid configuration")
            problem = Problem(500, "Invalid configuration", e.errors(), None, None)
            return func.HttpResponse(
                json.dumps(problem.to_dict()), status_code=500, mimetype="application/problem+json"
            )
       
        except ValueError as ve:
            logger.exception(ve.args[0])
            problem = Problem(502, "Missing or invalid value provided", ve.args[0], None, None)
            return func.HttpResponse(
                json.dumps(problem.to_dict()), status_code=502, mimetype="application/problem+json"
            )

        # Validazione modello
        try:
            req_body = req.get_json()
            request = RagOrchestratorRequest.model_validate(req_body)

            # Elimina la history dal tracciamento
            # del req_body["interactions"]
            logger.track_event(
                event_types.rag_orchestrator_requested_event,
                {
                    "requestBody": json.dumps(req_body, ensure_ascii=False).encode("utf-8"),
                    "callerService": consumer.name
                },
            )

            async with aiohttp.ClientSession(raise_for_status=True, trust_env=True) as session:
                query_response = await a_get_query_response(request, logger, session, consumer)
                json_content = json.dumps(query_response, ensure_ascii=False, default=lambda x: x.__dict__).encode(
                    "utf-8"
                )

                logger.track_event(
                    event_types.rag_orchestrator_performed_event,
                    {"response-body": json_content, "source": "CQA" if query_response.cqa_data else "LLM"},
                )

                return func.HttpResponse(json_content, mimetype="application/json")

        except ValidationError as e:            
            problem = Problem(422, "Bad Request", e.errors(), None, None)
            return func.HttpResponse(
                json.dumps(problem.to_dict()), status_code=422, mimetype="application/problem+json"
            )
        except ValueError as ve:
            problem = Problem(422, "Bad Request", str(ve), None, None)            
            return func.HttpResponse(
                json.dumps(problem.to_dict()), status_code=422, mimetype="application/problem+json"
            )
        except CustomPromptParameterError as e:
            logger.exception(e.args[0])
            problem = Problem(e.error_code, "Error prompt", e.args[0], None, None)
            return func.HttpResponse(
                json.dumps(problem.to_dict()), status_code=e.error_code, mimetype="application/problem+json"
            )        
        except Exception as e:         
            logger.exception(e)
            problem = Problem(500, "Internal server error", str(e), None, None)
            return func.HttpResponse(
                json.dumps(problem.to_dict(), default=str, ensure_ascii=False), status_code=500, mimetype="application/problem+json"
            )