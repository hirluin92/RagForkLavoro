from typing import Any, Dict, Optional
from pydantic import BaseModel


class TemplateResolveResponse:
    def __init__(self, resolved_template: str, parameters: list[str], validation_messages: list[dict[str, Any]]):
        self.resolved_template = resolved_template
        self.parameters = parameters
        self.validation_messages = validation_messages