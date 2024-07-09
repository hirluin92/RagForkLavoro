import json

import azure.functions as func
from pydantic import ValidationError

from models.apis.tagging_request_body import TaggingRequestBody
from logics.tagging import a_get_files_tags
from services.logging import LoggerBuilder
from utils.http_problem import Problem
import constants.event_types as event_types

bp = func.Blueprint()


@bp.route(route="metadataTagging", auth_level=func.AuthLevel.ANONYMOUS, methods=['POST'])
async def metadataTagging(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    with LoggerBuilder(__name__, context) as logger:
        logger.info('Metadata tagging request.')

        try:
            req_body = req.get_json()
            request_body = TaggingRequestBody.model_validate(req_body)
            filenames = [item.data.fileUrl for item in request_body.values]
            results = await a_get_files_tags(request_body, logger)
            return func.HttpResponse(results.toJSON(), mimetype='application/json')
        except ValidationError as e:
            problem = Problem(422, "Bad Request", e.errors(), None, None)
            return func.HttpResponse(json.dumps(problem.to_dict()),
                                     status_code=422,
                                     mimetype="application/problem+json")
        except Exception as e:
            logger.exception(e.args[0])
            logger.track_event(event_types.metadata_tagging_exception, {"filesUrl":f"{filenames}"})
            problem = Problem(500, "Internal server error",
                              e.args[0], None, None)
            return func.HttpResponse(
                json.dumps(problem.to_dict()),
                status_code=500,
                mimetype="application/problem+json")
