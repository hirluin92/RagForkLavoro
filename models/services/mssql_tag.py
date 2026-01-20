from dataclasses import dataclass, asdict
from enum import Enum

class EnumMonitorFormApplication(Enum):
    OnlyRag = 1
    Rag_MonitoringQuestion = 2
    OnlyMonitoringQuestion = 3
    
    def get_enum_name(value):
        val = next((item for item in EnumMonitorFormApplication if item.value == value), None)
        return val.name if val else None

@dataclass
class MsSqlTag:
    name: str
    description: str
    enable_cqa: bool = None
    enable_enrichment: bool = None
    id_monitoring_question: int = None
    desc_monitoring_question: str = None
    
@dataclass
class PromptVersionInfo:
    id: str
    version: str
    type: str