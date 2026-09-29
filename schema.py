from pydantic import BaseModel, ConfigDict
from typing import Dict, Any


class CUAOutput(BaseModel):
    thought: str
    step: str
    action: str
    arguments: Dict[str, Any]


class ContextMemoryEntry(BaseModel):
    thought: str
    step: str