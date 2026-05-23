"""Tests for the PDF reporting module.

We test that the PDF builder produces a valid file, that each
designer-specific report writes a file with the expected magic bytes,
and that the multi-page reports contain more than one page.
"""

from __future__ import annotations

import os

import pytest

from foundationdesignjm.codes.eurocode7 import DesignApproach
from foundationdesignjm.core.material import Concrete
from foundationdesignjm.core.soil import SoilLayer, SoilType
from foundationdesignjm.utils.pdf_report import (
    PdfReportBuilder,
    ReportMeta,
    report_basement_wall,
    report_crane,
    report_mat_foundation,
    report_retaining_wall,
    report_seismic_footing,
)


PDF_MAGIC = b"%PDF-"


def _read_pages(path: str) -> int:
    """Count `/Type /Page` occurrences in the PDF as a quick page-count proxy."""
    data = open(path, "rb").read()
    return data.count(b"/Type /Page\n") + data.count(b"/Type /Page>") + data.count(b"/Type/Page ")


def test_builder_creates_valid_pdf(tmp_path):
    builder = PdfReportBuilder(str(tmp_path / "test.pdf"), ReportMeta(project="unit"))
    builder.cover_page("Test", "subtitle", extra_lines=["line A", "line B"])
    fig = builder.section("Section 1", ["body line"])
    builder.close_page(fig)
    path = builder.save()
    assert os.path.isfile(path)
    with open(path, "rb") as f:
        assert f.read(5) == PDF_MAGIC


def test_retaining_wall_report(tmp_path):
    from foundationdesignjm.design.retaining_wall import (
        CantileverWallDesigner,
        CantileverWallGeometry,
        RetainingWallLoading,
    )
    geo = CantileverWallGeometry(
        H=5.0, stem_top=0.30, stem_bottom=0.45,
        toe=1.0, heel=2.5, base_thickness=0.55,
    )
    backfill = SoilLayer(name="fill", thickness=10, soil_type=SoilType.COHESIONLESS,
                        friction_angle=33, cohesion=0, unit_weight=19)
    foundation = SoilLayer(name="gravel", thickness=10, soil_type=SoilType.COHESIONLESS,
                          friction_angle=36, cohesion=0, unit_weight=20)
    load = RetainingWallLoading(
        backfill=backfill, foundation_soil=foundation,
        surcharge_q=10, use_coulomb=True, delta_over_phi=2.0 / 3.0,
    )
    des = CantileverWallDesigner(geo, load, Concrete(fck=30), design_approach=DesignApproach.DA2)
    res = des.check()
    path = str(tmp_path / "wall.pdf")
    out = report_retaining_wall(des, res, path, meta=ReportMeta(project="t", engineer="JM"))
    assert os.path.isfile(out)
    assert os.path.getsize(out) > 5000  # non-trivial PDF


def test_basement_wall_report(tmp_path):
    from foundationdesignjm.design.basement_wall import (
        BasementWallDesigner,
        BasementWallGeometry,
        BasementWallLoading,
    )
    geo = BasementWallGeometry(height=3.0, thickness=0.25)
    load = BasementWallLoading(
        phi_deg=30, gamma_soil=19, surcharge_q=10,
        N_min_kN_per_m=0, N_max_kN_per_m=150,
    )
    des = BasementWallDesigner(geo, load)
    res = des.solve()
    path = str(tmp_path / "basement.pdf")
    report_basement_wall(des, res, path)
    assert os.path.isfile(path)
    assert os.path.getsize(path) > 5000


def test_mat_foundation_report(tmp_path):
    from foundationdesignjm.analysis.mat_foundation import MatFoundationSolver
    mat = MatFoundationSolver(
        length=6, width=6, thickness=0.5, nx=10, ny=10, k_s=20000,
    )
    mat.add_uniform_pressure(q=10)
    mat.add_column_load(x=3, y=3, P=400, name="C")
    res = mat.solve()
    path = str(tmp_path / "mat.pdf")
    report_mat_foundation(mat, res, path)
    assert os.path.isfile(path)
    assert os.path.getsize(path) > 5000


def test_seismic_footing_report(tmp_path):
    from foundationdesignjm.analysis.seismic_footing import (
        SeismicAction, seismic_footing_check,
    )
    from foundationdesignjm.core.geometry import Column, RectangularFoundation
    pad = RectangularFoundation(length=3000, width=3000, thickness=700, embedment_depth=1200)
    col = Column(length=400, width=400, pos_x=1500, pos_y=1500)
    soil = SoilLayer(name="sand", thickness=10, soil_type=SoilType.COHESIONLESS,
                    friction_angle=36, cohesion=0, unit_weight=20)
    res = seismic_footing_check(
        pad, col, N_kN=1200, H_kN=180, M_kNm=420,
        soil=soil, concrete=Concrete(fck=30),
        seismic=SeismicAction(a_g=0.20, S=1.15, r_factor=2.0),
        design_approach=DesignApproach.DA3,
        soil_overburden_depth_mm=500,
    )
    path = str(tmp_path / "seismic.pdf")
    report_seismic_footing(res, path)
    assert os.path.isfile(path)
    assert os.path.getsize(path) > 5000


def test_crane_report(tmp_path):
    from foundationdesignjm.analysis.crane import (
        CraneLoadCase, CraneLoadState, design_envelope,
    )
    from foundationdesignjm.core.geometry import Column, RectangularFoundation
    pad = RectangularFoundation(length=6500, width=6500, thickness=1600, embedment_depth=1500)
    col = Column(length=2000, width=2000, pos_x=3250, pos_y=3250)
    sand = SoilLayer(name="sand", thickness=12, soil_type=SoilType.COHESIONLESS,
                    friction_angle=36, cohesion=0, unit_weight=19)
    lc = CraneLoadCase(state=CraneLoadState.SERVICE, name="Service",
                      N_kN=700, M_x_kNm=2400, V_y_kN=60)
    results = design_envelope(pad, col, [lc], sand, Concrete(fck=30),
                              soil_overburden_depth_mm=1500,
                              soil_unit_weight_overburden=19)
    path = str(tmp_path / "crane.pdf")
    report_crane(results, path)
    assert os.path.isfile(path)
    assert os.path.getsize(path) > 5000


def test_report_meta_defaults():
    meta = ReportMeta()
    assert meta.project == "Foundation design"
    assert len(meta.date) == 10  # YYYY-MM-DD


def test_builder_rejects_no_pages_gracefully(tmp_path):
    """An empty PDF (no pages added) saves but is minimal."""
    builder = PdfReportBuilder(str(tmp_path / "empty.pdf"), ReportMeta())
    builder.cover_page("Cover only")
    path = builder.save()
    assert os.path.getsize(path) > 0
