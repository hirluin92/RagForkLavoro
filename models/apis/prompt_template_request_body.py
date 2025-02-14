from typing import Any, Dict, Optional
from pydantic import BaseModel


class TemplateResolveRequest(BaseModel):
    template: str
    context: Optional[dict[str, Any]] = None