"""Dataclasses + enums del sistema de jobs."""
from __future__ import annotations
import enum
import time
import uuid
from dataclasses import dataclass, field, asdict


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobKind(str, enum.Enum):
    """Categoriza un job. En FoundationDesignJm sólo se usa NUMERICAL."""
    NUMERICAL = "numerical"


@dataclass
class JobRecord:
    """Estado persistible de un job."""
    id: str
    kind: JobKind
    task_name: str
    status: JobStatus = JobStatus.QUEUED
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    progress: float = 0.0
    message: str = ""
    payload: dict = field(default_factory=dict)
    result: dict | None = None
    error: str | None = None

    @staticmethod
    def new(kind: JobKind, task_name: str, payload: dict) -> "JobRecord":
        return JobRecord(
            id=uuid.uuid4().hex[:16],
            kind=kind,
            task_name=task_name,
            payload=payload,
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["status"] = self.status.value
        return d


@dataclass
class ProgressUpdate:
    """Reportado por un task durante su ejecución."""
    progress: float
    message: str = ""
