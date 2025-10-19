from typing import Literal, Optional

from pydantic import BaseModel


class Formatter(BaseModel):
    target_tool: str = ""
    prompt: str = ""


class Orchestrator(BaseModel):
    target_tool: str = ""
    next_tool: str = ""
    prompt: str = ""
    action: Literal["pre", "post"] = "pre"


class OrchestratorPluginConfig(BaseModel):
    formatter: Optional[Formatter] = None
    orchestrator: Optional[Orchestrator] = None
