import json
import azure.functions as func
from pydantic import ValidationError
from constants import event_types
from services.logging import LoggerBuilder
from utils.http_problem import Problem
from models.apis.convert_docx_to_md_request_body import ConvertDocxToMdRequestBody
from logics.convert_docx_to_md import a_extract_hyperlink_from_files
from utils.settings import get_storage_settings

bp = func.Blueprint()


@bp.route(route="convertDocxToMd", auth_level=func.AuthLevel.FUNCTION, methods=['POST'])
async def convert_docx_to_md(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    with LoggerBuilder(__name__, context) as logger:
        logger.info('Convert DOCX to MD request.')
        try:
            get_storage_settings()
        except ValidationError as err:
            logger.exception(str(err))
            problem = Problem(
                500, "Invalid storage account configuration", err.errors(), None, None)
            return func.HttpResponse(json.dumps(problem.to_dict()),
                                     status_code=500,
                                     mimetype="application/problem+json")
        try:
            req_body = req.get_json()
            logger.track_event(event_types.convert_docx_to_md,
                               {
                                   "request-body":  json.dumps(req_body)
                               })
            request_body = ConvertDocxToMdRequestBody.model_validate(req_body)
            result = await a_extract_hyperlink_from_files(request_body, context)
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
            problem = Problem(500, "Internal server error",
                              str(err), None, None)
            return func.HttpResponse(
                json.dumps(problem.to_dict()),
                status_code=500,
                mimetype="application/problem+json")
