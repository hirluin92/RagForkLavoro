
from pydantic import ValidationError 
from logics.ai_query_service_factory import AiQueryServiceFactory
from models.apis.rag_orchestrator_request import RagOrchestratorRequest
import json
from services.logging import LoggerBuilder
import azure.functions as func
from utils.http_problem import Problem
from utils.settings import (
    get_mistralai_settings,
    get_mssql_settings,
    get_openai_settings,
    get_storage_settings
    ) 
bp = func.Blueprint() 

@bp.route(route="augmentQuery", auth_level=func.AuthLevel.FUNCTION, methods=['POST'])
async def a_augment_query(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    with LoggerBuilder(__name__, context) as logger:
        logger.info('Augment query request')

    try:
        get_mistralai_settings()
        get_mssql_settings()
        get_openai_settings()
        get_storage_settings()
    except ValidationError as e:
        problem = Problem(500, "Invalid configuration", e.errors(), None, None)
        logger.exception("Invalid configuration")
        return func.HttpResponse(json.dumps(problem.to_dict()),
                                status_code=500,
                                    mimetype="application/problem+json")


    try:
        req_body = req.get_json()
        request = RagOrchestratorRequest.model_validate(req_body)
        
        language_service = AiQueryServiceFactory.get_instance(request.llm_model_id)
        result = await language_service.a_do_query_enrichment(request, logger)

        if result:
            json_content = json.dumps(result.model_dump())
            return func.HttpResponse(json_content, mimetype="application/json")
    
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