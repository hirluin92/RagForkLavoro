import aiohttp
from pydantic import ValidationError
import requests
from logics.ai_query_service_factory import AiQueryServiceFactory
from models.apis.rag_orchestrator_request import RagOrchestratorRequest
import json
from services.logging import LoggerBuilder
import azure.functions as func
from services.prompt_editor import a_get_enrichment_prompt_data
from utils.access_control_handler import handle_access_control
from utils.http_problem import Problem
from utils.settings import get_mistralai_settings, get_mssql_settings, get_openai_settings, get_storage_settings

bp = func.Blueprint()


@bp.route(route="augmentQuery", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
async def a_augment_query(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    with LoggerBuilder(__name__, context) as logger:
        logger.info("Augment query request")

    # Validazione body JSON PRIMA di handle_access_control per ottenere model_name
    try:
        req_body = req.get_json()
        request = RagOrchestratorRequest.model_validate(req_body)
    except ValidationError as e:
        problem = Problem(422, "Bad Request", e.errors(), None, None)
        return func.HttpResponse(json.dumps(problem.to_dict()), status_code=422, mimetype="application/problem+json")
    except Exception as e:
        problem = Problem(422, "Bad Request", f"Invalid JSON body: {str(e)}", None, None)
        return func.HttpResponse(json.dumps(problem.to_dict()), status_code=422, mimetype="application/problem+json")

    try:
        # Passa model_name a handle_access_control
        consumer = access_control = await handle_access_control(req, logger, model_name=request.model_name)

        get_mistralai_settings()
        get_mssql_settings()
        get_openai_settings()
        get_storage_settings()
    except ValidationError as e:
        problem = Problem(500, "Invalid configuration", e.errors(), None, None)
        logger.exception("Invalid configuration")
        return func.HttpResponse(json.dumps(problem.to_dict()), status_code=500, mimetype="application/problem+json")
    except Exception as e:
        logger.exception(str(e))
        problem = Problem(500, "Internal server error", str(e), None, None)
        return func.HttpResponse(json.dumps(problem.to_dict()), status_code=500, mimetype="application/problem+json")

    try:

        # Get AI service (OpenAI or Mistral)
        language_service = AiQueryServiceFactory.get_instance(request.llm_model_id)

        # Compute enrichment
        async with aiohttp.ClientSession(raise_for_status=True) as session:
            # API get prompts
            enrichment_prompt_data = await a_get_enrichment_prompt_data(request.prompts, logger, session)

            # Verify llm model id request and prompts model from editor
            if request.llm_model_id != enrichment_prompt_data.llm_model:
                raise requests.exceptions.HTTPError(
                    "Bad Request: The request llm model id  is different from prompt editor llm model.", response=None
                )
            result = await language_service.a_do_query_enrichment(
                request, enrichment_prompt_data, logger, consumer
            )
            json_content = json.dumps(result.model_dump())
            return func.HttpResponse(json_content, mimetype="application/json")

    except ValidationError as e:
        problem = Problem(422, "Bad Request", e.errors(), None, None)
        return func.HttpResponse(json.dumps(problem.to_dict()), status_code=422, mimetype="application/problem+json")
    except ValueError as ve:
        problem = Problem(422, "Bad Request", str(ve), None, None)
        return func.HttpResponse(
            json.dumps(problem.to_dict()), status_code=422, mimetype="application/problem+json"
        )
    except Exception as e:
        logger.exception(str(e))
        problem = Problem(500, "Internal server error", str(e), None, None)
        return func.HttpResponse(json.dumps(problem.to_dict()), status_code=500, mimetype="application/problem+json")
