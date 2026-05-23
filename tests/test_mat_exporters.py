"""Tests for SAFE and JSON mat-foundation exporters."""

from __future__ import annotations

import json
import os

from foundationdesignjm.analysis.mat_foundation import MatFoundationSolver
from foundationdesignjm.utils import export_mat_to_json, export_mat_to_safe


def _build_small_mat() -> MatFoundationSolver:
    mat = MatFoundationSolver(
        length=6.0, width=5.0, thickness=0.5,
        nx=6, ny=5, k_s=20000.0,
    )
    mat.add_uniform_pressure(q=12.0)
    mat.add_column_load(x=2.0, y=2.0, P=400.0, name="P1")
    mat.add_column_load(x=4.0, y=3.0, P=520.0, Mx=15, name="P2")
    return mat


def test_safe_export_emits_expected_tables(tmp_path):
    mat = _build_small_mat()
    path = export_mat_to_safe(
        mat, str(tmp_path / "model.s2k"), fck_MPa=30, model_name="UnitTest",
    )
    assert os.path.isfile(path)
    text = open(path, encoding="utf-8").read()
    # Each expected section must be present
    for table in (
        '"PROGRAM CONTROL"',
        '"MATERIAL PROPERTIES 01 - GENERAL"',
        '"SLAB PROPERTIES"',
        '"SOIL SUBGRADE PROPERTIES"',
        '"POINT COORDINATES"',
        '"AREA OBJECT CONNECTIVITIES"',
        '"AREA OBJECT SLAB ASSIGNMENTS"',
        '"AREA OBJECT SOIL ASSIGNMENTS"',
        '"AREA OBJECT UNIFORM LOADS"',
        '"POINT LOAD ASSIGNMENTS"',
    ):
        assert table in text
    # Subgrade value must match
    assert "Subgrade=20000" in text
    # Column load (P=520) appears with negative FZ (SAFE +Z up)
    assert "FZ=-400" in text or "FZ=-400.0" in text
    assert "FZ=-520" in text or "FZ=-520.0" in text


def test_json_export_is_valid_and_complete(tmp_path):
    mat = _build_small_mat()
    res = mat.solve()
    path = export_mat_to_json(mat, res, str(tmp_path / "results.json"))
    assert os.path.isfile(path)
    payload = json.loads(open(path, encoding="utf-8").read())

    # Schema sanity
    assert {"meta", "mesh", "loads", "results"} <= set(payload)
    assert payload["meta"]["length_m"] == 6.0
    assert payload["meta"]["k_s_kN_m3"] == 20000.0
    assert len(payload["mesh"]["nodes_xy"]) == mat.n_nodes
    assert len(payload["mesh"]["elements"]) == mat.n_elems
    assert len(payload["results"]["w_mm"]) == mat.n_nodes
    assert len(payload["results"]["M_xx_kNm_per_m"]) == mat.n_elems
    assert payload["results"]["converged"] is True


def test_safe_export_handles_no_column_loads(tmp_path):
    """Self-weight-only model must still produce a valid .s2k."""
    mat = MatFoundationSolver(
        length=4.0, width=4.0, thickness=0.4,
        nx=4, ny=4, k_s=15000.0,
    )
    mat.add_uniform_pressure(q=10.0)
    path = export_mat_to_safe(mat, str(tmp_path / "nopt.s2k"), fck_MPa=25)
    text = open(path, encoding="utf-8").read()
    assert '"AREA OBJECT UNIFORM LOADS"' in text
    # No POINT LOAD ASSIGNMENTS table for this model
    assert '"POINT LOAD ASSIGNMENTS"' not in text
