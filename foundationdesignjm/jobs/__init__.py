"""Sistema de jobs asíncrono de FoundationDesignJm.

Todo el trabajo en este paquete es NUMERICAL (numpy/scipy puro), por lo
que no hay worker COM dedicado: se usa un ThreadPoolExecutor.
"""
from __future__ import annotations
from .models import JobRecord, JobStatus, JobKind, ProgressUpdate
from .store import JobStore
from .queue import (
    JobQueue, register_task, numerical_task,
    get_task, list_tasks,
)
from . import tasks_builtin  # noqa: F401 — registra los tasks built-in

__all__ = [
    "JobRecord", "JobStatus", "JobKind", "ProgressUpdate",
    "JobStore", "JobQueue",
    "register_task", "numerical_task",
    "get_task", "list_tasks",
]
