
from dataclasses import dataclass
from typing import Any


@dataclass
class CQAResponse:
    text_answer: str
    cqa_data: Any