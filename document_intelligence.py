import json

import azure.functions as func 
from models.apis.document_intelligence_request_body import DocumentIntelligenceRequestBody
from pydantic import ValidationError
from logics.document_intelligence import a_get_documents_content
from services.logging import LoggerBuilder
from utils.http_problem import Problem
from utils.settings import get_document_intelligence_settings

bp = func.Blueprint()

@bp.route(route="documentIntelligence", auth_level=func.AuthLevel.ANONYMOUS, methods=['POST'])
async def document_intelligence(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    with LoggerBuilder(__name__, context) as logger:
        logger.info('Document intelligence request')
        outputFormat = req.params.get('outputFormat')
        try:
            get_document_intelligence_settings()
        except ValidationError as e:
            problem = Problem(500, "Invalid configuration", e.errors(), None, None)
            return func.HttpResponse(json.dumps(problem.to_dict()),
                                    status_code=500,
                                        mimetype="application/problem+json")

        try:
            req_body = req.get_json()
            request_body = DocumentIntelligenceRequestBody.model_validate(req_body)
            result = await a_get_documents_content(request_body, outputFormat, logger)
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