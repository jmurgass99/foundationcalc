"""Generate professional PDF reports for every major designer.

Builds five PDFs in `out/`:
  - wall_report.pdf       (cantilever retaining wall)
  - basement_report.pdf   (basement wall)
  - mat_report.pdf        (mat foundation)
  - seismic_report.pdf    (seismic footing)
  - crane_report.pdf      (tower-crane foundation)

Each report has a cover page, ULS checks, structural forces and
diagrams suitable to hand to a client. The only dependency is
matplotlib (already required for the library).

Run with:   python -m examples.pdf_reports_example
"""

from __future__ import annotations

import os

from foundationcalc.analysis.crane import (
    CraneLoadCase, CraneLoadState, design_envelope,
)
from foundationcalc.analysis.mat_foundation import MatFoundationSolver
from foundationcalc.analysis.seismic_footing import (
    SeismicAction, seismic_footing_check,
)
from foundationcalc.codes.eurocode7 import DesignApproach
from foundationcalc.core.geometry import Column, RectangularFoundation
from foundationcalc.core.material import Concrete
from foundationcalc.core.soil import SoilLayer, SoilType
from foundationcalc.design.basement_wall import (
    BasementWallDesigner, BasementWallGeometry, BasementWallLoading,
)
from foundationcalc.design.retaining_wall import (
    CantileverWallDesigner, CantileverWallGeometry, RetainingWallLoading,
)
from foundationcalc.utils.pdf_report import (
    ReportMeta,
    report_basement_wall,
    report_crane,
    report_mat_foundation,
    report_retaining_wall,
    report_seismic_footing,
)


def _meta(project: str) -> ReportMeta:
    return ReportMeta(
        project=project, client="Demo Client",
        engineer="J. Murga", job_code="FDJM-2026-001",
    )


def main() -> None:
    os.makedirs("out", exist_ok=True)
    sand = SoilLayer(name="sand", thickness=10, soil_type=SoilType.COHESIONLESS,
                    friction_angle=36, cohesion=0, unit_weight=20)
    C30 = Concrete(fck=30)

    # 1. Retaining wall ----------------------------------------------------
    geo_w = CantileverWallGeometry(
        H=5.0, stem_top=0.30, stem_bottom=0.45,
        toe=1.0, heel=2.5, base_thickness=0.55, embedment_front=0.8,
    )
    backfill = SoilLayer(name="fill", thickness=10, soil_type=SoilType.COHESIONLESS,
                        friction_angle=33, cohesion=0, unit_weight=19)
    load_w = RetainingWallLoading(
        backfill=backfill, foundation_soil=sand,
        surcharge_q=10, use_coulomb=True, delta_over_phi=2/3,
    )
    des_w = CantileverWallDesigner(geo_w, load_w, C30, design_approach=DesignApproach.DA2)
    res_w = des_w.check()
    out1 = report_retaining_wall(des_w, res_w, "out/wall_report.pdf",
                                  meta=_meta("Cantilever retaining wall"))

    # 2. Basement wall -----------------------------------------------------
    geo_b = BasementWallGeometry(
        height=3.5, thickness=0.30,
        eccentricity_top=0.05, eccentricity_base=0.10,
    )
    load_b = BasementWallLoading(
        phi_deg=30, gamma_soil=19, surcharge_q=10,
        N_min_kN_per_m=0, N_max_kN_per_m=200,
    )
    des_b = BasementWallDesigner(geo_b, load_b)
    res_b = des_b.solve()
    out2 = report_basement_wall(des_b, res_b, "out/basement_report.pdf",
                                meta=_meta("Single-basement wall"))

    # 3. Mat foundation ----------------------------------------------------
    mat = MatFoundationSolver(
        length=12, width=10, thickness=0.7, nx=24, ny=20, k_s=25000,
    )
    mat.add_uniform_pressure(q=17.5)
    for x, y, P, name in [(2,2,900,"P1"),(6,2,1100,"P2"),(10,2,950,"P3"),
                          (2,8,920,"P4"),(6,8,1150,"P5"),(10,8,980,"P6")]:
        mat.add_column_load(x=x, y=y, P=P, name=name)
    res_m = mat.solve()
    out3 = report_mat_foundation(mat, res_m, "out/mat_report.pdf",
                                 meta=_meta("Mat / raft foundation"))

    # 4. Seismic footing ---------------------------------------------------
    pad = RectangularFoundation(length=3000, width=3000, thickness=700, embedment_depth=1200)
    col = Column(length=400, width=400, pos_x=1500, pos_y=1500)
    res_s = seismic_footing_check(
        pad, col, N_kN=1200, H_kN=180, M_kNm=420,
        soil=sand, concrete=C30,
        seismic=SeismicAction(a_g=0.20, S=1.15, r_factor=2.0),
        design_approach=DesignApproach.DA3,
        soil_overburden_depth_mm=500,
    )
    out4 = report_seismic_footing(res_s, "out/seismic_report.pdf",
                                  meta=_meta("Seismic footing (EN 1998-5)"))

    # 5. Tower crane -------------------------------------------------------
    pad_c = RectangularFoundation(length=6500, width=6500, thickness=1600, embedment_depth=1500)
    col_c = Column(length=2000, width=2000, pos_x=3250, pos_y=3250)
    sand_c = SoilLayer(name="sand", thickness=12, soil_type=SoilType.COHESIONLESS,
                       friction_angle=36, cohesion=0, unit_weight=19)
    service = CraneLoadCase(state=CraneLoadState.SERVICE, name="Service",
                           N_kN=700, M_x_kNm=2400, V_y_kN=60)
    oos = CraneLoadCase(state=CraneLoadState.OUT_OF_SERVICE, name="Storm",
                       N_kN=500, M_x_kNm=3200, V_y_kN=130, is_wind_dominant=True)
    crane_results = design_envelope(
        pad_c, col_c, [service, oos], sand_c, C30,
        soil_overburden_depth_mm=1500, soil_unit_weight_overburden=19,
    )
    out5 = report_crane(crane_results, "out/crane_report.pdf",
                        meta=_meta("Tower-crane foundation"))

    print("Generated reports:")
    for p in (out1, out2, out3, out4, out5):
        print(f"  {p}  ({os.path.getsize(p):,} bytes)")


if __name__ == "__main__":
    main()
