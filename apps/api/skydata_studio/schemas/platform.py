from typing import Literal

from pydantic import BaseModel


class Capability(BaseModel):
    code: str
    name: str
    description: str
    status: Literal["FOUNDATION", "SCAFFOLDED", "PLANNED", "READY"]
    phase: int


class PlatformSummary(BaseModel):
    product: str
    subtitle: str
    theme: str
    current_phase: str
    boundary: str
    capabilities: list[Capability]


class RoadmapPhase(BaseModel):
    number: int
    name: str
    status: Literal["IN_PROGRESS", "NEXT", "PLANNED", "COMPLETE"]
