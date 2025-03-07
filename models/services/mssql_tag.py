from dataclasses import dataclass
from enum import Enum

class EnumMonitoringQuestion(Enum):
    OnlyRag = 0
    Rag_MonitoringQuestion = 1
    OnlyMonitoringQuestion = 2
    
    def get_enum_name(value):
        val = next((item for item in EnumMonitoringQuestion if item.value == value), None)
        return val.name if val else None

@dataclass
class MsSqlTag:
    name: str
    description: str
    enable_cqa: bool = None
    enable_enrichment: bool = None
    id_monitoring_question: int = None
    enable_monitoring_question: bool = None
    desc_monitoring_question: str = None
    
@dataclass
class PromptVersionInfo:
    id: str
    version: str
    type: str