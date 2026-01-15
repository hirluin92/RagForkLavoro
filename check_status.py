import json
import azure.functions as func
from services.logging import LoggerBuilder

bp = func.Blueprint()


@bp.route(route="check-status", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
async def check_status(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    with LoggerBuilder(__name__, context) as logger:
        logger.info("Check status request.")
        return func.HttpResponse(json.dumps("RAG: OK"), status_code=200, mimetype="application/problem+json")
