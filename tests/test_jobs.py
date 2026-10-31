"""Tests del sistema de jobs (store + queue + tasks built-in)."""
from __future__ import annotations
import time
import pytest

from foundationcalc.jobs import (
    JobStore, JobQueue, JobRecord, JobKind, JobStatus,
    register_task, list_tasks,
)


@pytest.fixture
def tmp_store(tmp_path):
    return JobStore(db_path=tmp_path / "jobs.db")


def test_store_save_get_roundtrip(tmp_store):
    rec = JobRecord.new(JobKind.NUMERICAL, "design_footing",
                        {"L_x": 2.0, "L_y": 2.0, "thickness": 0.5})
    tmp_store.save(rec)
    got = tmp_store.get(rec.id)
    assert got is not None
    assert got.id == rec.id
    assert got.task_name == "design_footing"
    assert got.status == JobStatus.QUEUED


def test_builtin_tasks_registered():
    names = list_tasks()
    assert "design_footing" in names
    assert "design_wall" in names
    assert "design_pile_axial" in names
    assert "bearing_capacity" in names
    assert "mononobe_okabe" in names


def test_enqueue_runs_to_success(tmp_store):
    q = JobQueue(store=tmp_store, numerical_workers=2)
    try:
        rec = q.enqueue("design_footing", {
            "L_x": 2.5, "L_y": 2.5, "thickness": 0.6,
            "N": 1500.0,
        })
        # Wait
        deadline = time.time() + 5
        while time.time() < deadline:
            got = tmp_store.get(rec.id)
            if got.status in (JobStatus.SUCCESS, JobStatus.FAILED):
                break
            time.sleep(0.05)
        got = tmp_store.get(rec.id)
        assert got.status == JobStatus.SUCCESS, got.error
        assert got.result is not None
        assert "pressures" in got.result
    finally:
        q.shutdown(wait=True)


def test_enqueue_unknown_task_raises(tmp_store):
    q = JobQueue(store=tmp_store, numerical_workers=1)
    try:
        with pytest.raises(ValueError):
            q.enqueue("does_not_exist", {})
    finally:
        q.shutdown(wait=True)


def test_failing_task_records_error(tmp_store):
    @register_task("__test_failing__")
    def bad(payload, *, report_progress):
        raise RuntimeError("boom")

    q = JobQueue(store=tmp_store, numerical_workers=1)
    try:
        rec = q.enqueue("__test_failing__", {})
        deadline = time.time() + 5
        while time.time() < deadline:
            got = tmp_store.get(rec.id)
            if got.status in (JobStatus.SUCCESS, JobStatus.FAILED):
                break
            time.sleep(0.05)
        got = tmp_store.get(rec.id)
        assert got.status == JobStatus.FAILED
        assert got.error and "boom" in got.error
    finally:
        q.shutdown(wait=True)
