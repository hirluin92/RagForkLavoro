import json

import aiohttp
import azure.functions as func
from pydantic import ValidationError

from logics.delete_documents import a_delete_by_tag
from services.logging import LoggerBuilder
from utils.http_problem import Problem
from utils.settings import get_search_settings, get_storage_settings

bp = func.Blueprint()


@bp.route(route="deleteDocumentsByTag/{tag}", auth_level=func.AuthLevel.ANONYMOUS, methods=['DELETE'])
async def deleteDocuments(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    with LoggerBuilder(__name__, context) as logger:
        tag = req.route_params.get('tag', "")
        logger.info('DeleteDocumentsByTag request (tag:' + tag + ')')

        try:
            get_search_settings()
            get_storage_settings()
        except ValidationError as e:
            problem = Problem(500, "Invalid configuration",
                              e.errors(), None, None)
            logger.exception("Invalid configuration")
            return func.HttpResponse(json.dumps(problem.to_dict()),
                                     status_code=500,
                                     mimetype="application/problem+json")

        try:
            if len(tag) == 0:
                raise ValueError("Invalid tag")
            async with aiohttp.ClientSession(raise_for_status=True) as session:
                await a_delete_by_tag(tag,logger,session)
                return func.HttpResponse(status_code=204,
                                        mimetype="application/json")
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
