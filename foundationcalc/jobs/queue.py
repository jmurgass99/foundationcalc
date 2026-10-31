"""Job queue + dispatcher para FoundationCalc.

Todos los jobs son NUMERICAL (numpy/scipy), por lo que corren en un
ThreadPoolExecutor.
"""
from __future__ import annotations
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from .models import JobRecord, JobStatus, JobKind, ProgressUpdate
from .store import JobStore

log = logging.getLogger("foundationcalc.jobs")


_TASKS: dict[str, Callable] = {}


def register_task(name: str):
    """Decorator: registra una función como task ejecutable.

    Firma de la función:
        f(payload: dict, *, report_progress: Callable[[ProgressUpdate], None]) -> dict
    """
    def deco(fn: Callable) -> Callable:
        if name in _TASKS:
            log.warning("task '%s' ya registrada, sobrescribiendo", name)
        _TASKS[name] = fn
        return fn
    return deco


def numerical_task(name: str):
    """Alias semántico de register_task; en FoundationCalc todo es NUMERICAL."""
    def deco(fn):
        fn._fdj_job_kind = JobKind.NUMERICAL
        return register_task(name)(fn)
    return deco


def get_task(name: str) -> Callable | None:
    return _TASKS.get(name)


def list_tasks() -> list[str]:
    return sorted(_TASKS.keys())


class JobQueue:
    """Cola in-process basada en ThreadPoolExecutor."""

    def __init__(self, store: JobStore | None = None, *,
                 numerical_workers: int = 4) -> None:
        self.store = store or JobStore()
        self._numerical = ThreadPoolExecutor(max_workers=numerical_workers,
                                             thread_name_prefix="fdj-num")
        self._stop = threading.Event()
        self._cancelled: set[str] = set()

    # ----------- API pública -----------

    def enqueue(self, task_name: str, payload: dict | None = None) -> JobRecord:
        task = get_task(task_name)
        if task is None:
            raise ValueError(f"Task '{task_name}' no registrada")
        kind: JobKind = getattr(task, "_fdj_job_kind", JobKind.NUMERICAL)
        rec = JobRecord.new(kind=kind, task_name=task_name, payload=payload or {})
        self.store.save(rec)
        self._numerical.submit(self._run_job, rec.id)
        log.info("job %s encolado: %s (%s)", rec.id, task_name, kind.value)
        return rec

    def cancel(self, job_id: str) -> bool:
        rec = self.store.get(job_id)
        if rec is None or rec.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
            return False
        self._cancelled.add(job_id)
        if rec.status == JobStatus.QUEUED:
            rec.status = JobStatus.CANCELLED
            rec.finished_at = time.time()
            self.store.save(rec)
        return True

    def shutdown(self, *, wait: bool = True) -> None:
        self._stop.set()
        self._numerical.shutdown(wait=wait)

    # ----------- Internals -----------

    def _run_job(self, job_id: str) -> None:
        rec = self.store.get(job_id)
        if rec is None:
            return
        if job_id in self._cancelled:
            rec.status = JobStatus.CANCELLED
            rec.finished_at = time.time()
            self.store.save(rec)
            return
        task = get_task(rec.task_name)
        if task is None:
            rec.status = JobStatus.FAILED
            rec.error = f"task '{rec.task_name}' no encontrada"
            rec.finished_at = time.time()
            self.store.save(rec)
            return
        rec.status = JobStatus.RUNNING
        rec.started_at = time.time()
        self.store.save(rec)

        def report_progress(update: ProgressUpdate) -> None:
            rec.progress = max(0.0, min(1.0, update.progress))
            rec.message = update.message
            self.store.save(rec)

        try:
            result = task(rec.payload, report_progress=report_progress)
            rec.status = JobStatus.SUCCESS
            rec.progress = 1.0
            rec.result = result if isinstance(result, dict) else {"value": result}
        except Exception as exc:
            rec.status = JobStatus.FAILED
            rec.error = f"{type(exc).__name__}: {exc}"
            log.exception("job %s falló", job_id)
        finally:
            rec.finished_at = time.time()
            self.store.save(rec)
