import json

import azure.functions as func
from pydantic import ValidationError

from models.apis.chunking_empty_rows_request_body import ChunkingEmptyRowsRequestBody
from logics.split_data import a_custom_chunking
from services.logging import LoggerBuilder
from utils.http_problem import Problem

bp = func.Blueprint()


@bp.route(route="chunkingEmptyRows", auth_level=func.AuthLevel.ANONYMOUS, methods=['POST'])
async def chunking(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    with LoggerBuilder(__name__, context) as logger:
        logger.info('Chunking Empty Rows request.')
        try:
            req_body = req.get_json()
            request_body = ChunkingEmptyRowsRequestBody.model_validate(req_body)
            results = await a_custom_chunking(request_body, logger)
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