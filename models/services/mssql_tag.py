from dataclasses import dataclass

@dataclass
class MsSqlTag:
    name: str
    description: str
    
@dataclass
class PromptVersionInfo:
    id: str
    version: str
    type: str