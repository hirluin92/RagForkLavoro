import json

import azure.functions as func
from pydantic import ValidationError

from models.apis.tagging_request_body import TaggingRequestBody
from logics.tagging import a_get_files_tags
from services.logging import LoggerBuilder
from utils.http_problem import Problem

bp = func.Blueprint()


@bp.route(route="tagging", auth_level=func.AuthLevel.ANONYMOUS, methods=['POST'])
async def tagging(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    with LoggerBuilder(__name__, context) as logger:
        logger.info('Tagging request.')

        try:
            req_body = req.get_json()
            request_body = TaggingRequestBody.model_validate(req_body)
            results = await a_get_files_tags(request_body, logger)
            return func.HttpResponse(results.toJSON(), mimetype='application/json')
        except ValidationError as e:
            problem = Problem(422, "Bad Request", e.errors(), None, None)
            return func.HttpResponse(json.dumps(problem.to_dict()),
                                     status_code=422,
                                     mimetype="application/problem+json")
        except Exception as e:
            logger.exception(e.args[0])
            problem = Problem(500, "Internal server error",
                              e.args[0], None, None)
            return func.HttpResponse(
                json.dumps(problem.to_dict()),
                status_code=500,
                mimetype="application/problem+json")
