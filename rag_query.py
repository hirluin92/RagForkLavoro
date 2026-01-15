import json
import aiohttp
import azure.functions as func
from pydantic import ValidationError
import requests

import constants.event_types as event_types
from logics.ai_query_service_factory import AiQueryServiceFactory
from models.apis.rag_orchestrator_request import RagOrchestratorRequest
from services.prompt_editor import a_get_completion_prompt_data
from utils.http_problem import Problem
from services.logging import LoggerBuilder
from utils.access_control_handler import handle_access_control
from utils.settings import (
    get_mistralai_settings,
    get_openai_settings,
    get_prompt_settings,
    get_search_settings,
    get_storage_settings,
)

bp = func.Blueprint()


@bp.route(route="query", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
async def a_query(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    with LoggerBuilder(__name__, context) as logger:
        logger.info("Query request")

        try:
            consumer = access_control = await handle_access_control(req, logger)

            get_mistralai_settings()
            get_openai_settings()
            get_prompt_settings()
            get_search_settings()
            get_storage_settings()
        except ValidationError as e:
            problem = Problem(500, "Invalid configuration", e.errors(), None, None)
            logger.exception("Invalid configuration")
            return func.HttpResponse(
                json.dumps(problem.to_dict()), status_code=500, mimetype="application/problem+json"
            )

        try:
            req_body = req.get_json()
            request = RagOrchestratorRequest.model_validate(req_body)
            logger.track_event(
                event_types.rag_query_requested_event,
                {"request-body": json.dumps(req_body, ensure_ascii=False).encode("utf-8")},
            )

            # Get AI service (OpenAI or Mistral)
            language_service = AiQueryServiceFactory.get_instance(request.llm_model_id)

            async with aiohttp.ClientSession(raise_for_status=True) as session:
                # API get prompts
                completion_prompt_data = await a_get_completion_prompt_data(request.prompts, logger, session)

                # Verify llm model id request and prompts model from editor
                if request.llm_model_id != completion_prompt_data.llm_model:
                    raise requests.exceptions.HTTPError(
                        "Bad Request: The request llm model id  is different from prompt editor llm model.",
                        response=None,
                    )
                result = await language_service.a_do_query(
                    request, completion_prompt_data, logger, session, consumer
                )
                json_content = json.dumps(result, ensure_ascii=False, default=lambda x: x.__dict__).encode("utf-8")
                logger.track_event(event_types.rag_query_performed_event, {"response-body": json_content})

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
        except Exception as e:
            logger.exception(e.args[0])
            problem = Problem(500, "Internal server error", e.args[0], None, None)
            return func.HttpResponse(
                json.dumps(problem.to_dict()), status_code=500, mimetype="application/problem+json"
            )
