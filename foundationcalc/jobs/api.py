"""FastAPI router montable bajo /jobs.

Importa fastapi/pydantic perezosamente: si no están instalados, este
módulo es no-op y el resto de `foundationcalc.jobs` sigue funcionando.
"""
from __future__ import annotations

try:
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel
except Exception:  # pragma: no cover - opt dep
    APIRouter = None  # type: ignore
    HTTPException = None  # type: ignore
    BaseModel = object  # type: ignore

from .queue import JobQueue, list_tasks
from .models import JobStatus


_queue_instance: JobQueue | None = None


def set_queue(q: JobQueue) -> None:
    """Llamar al iniciar la app para inyectar la cola."""
    global _queue_instance
    _queue_instance = q


def _get_queue() -> JobQueue:
    if _queue_instance is None:
        raise HTTPException(503, "JobQueue no inicializada")
    return _queue_instance


if APIRouter is not None:
    router = APIRouter(prefix="/jobs", tags=["jobs"])

    class EnqueueRequest(BaseModel):
        task: str
        payload: dict = {}

    @router.get("/tasks")
    def get_tasks():
        return {"tasks": list_tasks()}

    @router.post("/enqueue")
    def enqueue(req: EnqueueRequest):
        q = _get_queue()
        try:
            rec = q.enqueue(req.task, req.payload)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        return rec.to_dict()

    @router.get("/{job_id}")
    def get_job(job_id: str):
        q = _get_queue()
        rec = q.store.get(job_id)
        if rec is None:
            raise HTTPException(404, f"Job {job_id} no encontrado")
        return rec.to_dict()

    @router.get("/")
    def list_jobs(status: str | None = None, limit: int = 50):
        q = _get_queue()
        st = JobStatus(status) if status else None
        return [r.to_dict() for r in q.store.list(status=st, limit=limit)]

    @router.delete("/{job_id}")
    def cancel_job(job_id: str):
        q = _get_queue()
        ok = q.cancel(job_id)
        if not ok:
            raise HTTPException(409, "No se puede cancelar (no existe o ya terminó)")
        return {"cancelled": job_id}
else:  # pragma: no cover
    router = None
