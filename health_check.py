import json
import azure.functions as func

bp = func.Blueprint()


@bp.route(route="health", auth_level=func.AuthLevel.ANONYMOUS, methods=['GET'])
async def health_check(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"status": "healthy", "version": "v1.0.1"}),
        status_code=200,
        mimetype="application/json"
    )
