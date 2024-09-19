import json

import aiohttp
import azure.functions as func
from pydantic import ValidationError

import constants.event_types as event_types
from logics.ai_query_service_factory import AiQueryServiceFactory
from models.apis.rag_query_request_body import RagQueryRequestBody
from utils.http_problem import Problem 
from services.logging import LoggerBuilder
from utils.settings import (
    get_app_settings,
    get_mistralai_settings,
    get_openai_settings,
    get_prompt_settings,
    get_search_settings,
    get_storage_settings
    )

bp = func.Blueprint() 

@bp.route(route="query", auth_level=func.AuthLevel.FUNCTION, methods=['POST'])
async def a_query(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    with LoggerBuilder(__name__, context) as logger:
        logger.info('Query request')
        
        try:
            get_app_settings()
            get_mistralai_settings()
            get_openai_settings()
            get_prompt_settings()
            get_search_settings()
            get_storage_settings()
        except ValidationError as e:
            problem = Problem(500, "Invalid configuration", e.errors(), None, None)
            logger.exception("Invalid configuration")
            return func.HttpResponse(json.dumps(problem.to_dict()),
                                    status_code=500,
                                        mimetype="application/problem+json")

        try:
            req_body = req.get_json()
            request_body = RagQueryRequestBody.model_validate(req_body)
            logger.track_event(event_types.rag_query_requested_event,
                            {
                               "request-body": json.dumps(req_body)
                            })
            language_service = AiQueryServiceFactory.get_instance(request_body.llm_model_id)
            async with aiohttp.ClientSession(raise_for_status=True) as session:
                result = await language_service.a_do_query(request_body, logger, session)
                logger.track_event(event_types.rag_query_performed_event,
                                {
                                "response-body": result.toJSON()
                                })
                return func.HttpResponse(result.toJSON(),
                                        mimetype="application/json")
        except ValidationError as e:
            problem = Problem(422, "Bad Request", e.errors(), None, None)
            return func.HttpResponse(json.dumps(problem.to_dict()),
                                    status_code=422,
                                        mimetype="application/problem+json")
        except Exception as e:
            logger.exception(e.args[0])
            problem = Problem(500, "Internal server error", e.args[0], None, None)
            return func.HttpResponse(
                json.dumps(problem.to_dict()),
                status_code= 500,
                mimetype="application/problem+json")