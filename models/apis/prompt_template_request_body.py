from typing import Any, Dict, Optional


class TemplateResolveRequest:
    def __init__(self, template: str, context: Optional[dict[str, Any]] = None):
        self.template = template
        self.context = context

    def to_dict(self):
        return {
            "template": self.template,
            "context": self.context
        }