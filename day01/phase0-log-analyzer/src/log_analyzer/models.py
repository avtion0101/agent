from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class LogEntry(BaseModel):
    """A validated record. Converting text to typed fields is the parser's job."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    timestamp: datetime
    level: LogLevel
    component: str = Field(min_length=1)
    latency_ms: float = Field(ge=0, allow_inf_nan=False)
    message: str = Field(min_length=1)


class ParseIssue(BaseModel):
    line_number: int
    reason: str


class AnalysisReport(BaseModel):
    total_lines: int
    valid_lines: int
    invalid_lines: int
    level_counts: dict[str, int]
    component_counts: dict[str, int]
    mean_latency_ms: float | None
    max_latency_ms: float | None
    invalid_examples: list[ParseIssue]
    elapsed_seconds: float
