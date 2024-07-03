import json

import azure.functions as func
from pydantic import ValidationError

from models.apis.tagging_request_body import TaggingRequestBody
from logics.split_data import custom_chunking
from services.logging import LoggerBuilder
from utils.http_problem import Problem

bp = func.Blueprint()


@bp.route(route="chunkingEmptyRows", auth_level=func.AuthLevel.ANONYMOUS, methods=['POST'])
async def tagging(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    with LoggerBuilder(__name__, context) as logger:
        logger.info('Tagging request.')
        return func.HttpResponse()