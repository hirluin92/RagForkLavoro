import json
import azure.functions as func
from pydantic import ValidationError
from services.logging import LoggerBuilder
from utils.http_problem import Problem
from models.apis.movefiles_request_body import MoveFilesRequestBody
from logics.move_files import a_move_all_data_response
from utils.settings import get_storage_settings

bp = func.Blueprint()


@bp.route(route="moveFiles", auth_level=func.AuthLevel.ANONYMOUS, methods=['POST'])
async def move_files(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    with LoggerBuilder(__name__, context) as logger:
        logger.info('Move files request.')
        try:
            get_storage_settings()
        except ValidationError as err:
            logger.exception(str(err))
            problem = Problem(500, "Invalid storage account configuration", err.errors(), None, None)
            return func.HttpResponse(json.dumps(problem.to_dict()),
                                     status_code=500,
                                     mimetype="application/problem+json")
        try:
            req_body = req.get_json()
            request_body = MoveFilesRequestBody.model_validate(req_body)
            result = await a_move_all_data_response(request_body, context)
            return func.HttpResponse(result.toJSON(),
                                        mimetype="application/json")
        except ValidationError as err:
            logger.exception(str(err))
            problem = Problem(422, "Bad Request", err.errors(), None, None)
            return func.HttpResponse(json.dumps(problem.to_dict()),
                                    status_code=422,
                                        mimetype="application/problem+json")
        except Exception as err:
            logger.exception(str(err))
            problem = Problem(500, "Internal server error", str(err), None, None)
            return func.HttpResponse(
                json.dumps(problem.to_dict()),
                status_code=500,
                mimetype="application/problem+json")
