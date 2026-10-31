"""Reverse design (optimizer) and pile-group example.

Two flows, run sequentially:

1. **Reverse design** — given a CPT log, a column load and a
   settlement limit, find the minimum square footing that passes all
   the checks. Also generate the PDF report of that final design.

2. **Pile group** — a 2 x 3 pile group of 0.8 m diameter piles spaced
   2.4 m carries V = 6 000 kN, H = 600 kN and M = 2 000 kN.m. We compute
   the per-pile forces using the rigid-cap formula plus group-efficiency
   corrections and identify the governing pile.

Run with:   python -m examples.reverse_design_and_pile_group_example
"""

from __future__ import annotations

import os

from foundationcalc.analysis.cpt import CPTProfile, CPTReading
from foundationcalc.analysis.cpt_to_design import design_footing_from_cpt
from foundationcalc.analysis.pile_group import (
    distribute_loads_rigid_cap, rectangular_group,
)
from foundationcalc.analysis.reverse_design import (
    CostModel, OptimizationGoal, optimize_footing_dimensions,
)
from foundationcalc.codes.eurocode7 import DesignApproach
from foundationcalc.core.geometry import RectangularFoundation
from foundationcalc.utils.pdf_report import (
    ReportMeta, report_cpt_to_design,
)


def _cpt() -> CPTProfile:
    readings = []
    for d in [0.5, 1, 1.5, 2, 2.5, 3]:
        readings.append(CPTReading(depth=d, q_c_MPa=6.0, f_s_kPa=40))
    for d in [3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7]:
        readings.append(CPTReading(depth=d, q_c_MPa=1.2, f_s_kPa=60, u_2_kPa=60))
    for d in [7.5, 8, 9, 10, 11, 12, 13, 14, 15]:
        readings.append(CPTReading(depth=d, q_c_MPa=18.0, f_s_kPa=80))
    return CPTProfile(
        readings=readings, water_table_depth_m=2.5,
        gamma_above_wt_kN_m3=18, gamma_below_wt_kN_m3=20,
    )


def main() -> None:
    os.makedirs("out", exist_ok=True)
    print("=" * 78)
    print("FoundationCalc - Reverse design + pile group")
    print("=" * 78)

    # --------------- 1. Reverse design --------------------------------
    print()
    print("--- Part 1: minimum square footing for V = 1500 kN ---")
    opt = optimize_footing_dimensions(
        _cpt(), load_kN=1500, founding_depth_m=1.5,
        design_approach=DesignApproach.DA2,
        settlement_limit_mm=50.0,
        cost_model=CostModel(),
        B_min_mm=800, B_max_mm=6000, thickness_mm=600,
        goal=OptimizationGoal.MIN_AREA,
    )
    print(f"  Iterations:       {len(opt.history)}")
    print(f"  Optimum B = L:    {opt.best.B * 1000:.0f} mm")
    print(f"  Bearing util:     {opt.best.bearing_utilization * 100:.1f} %")
    print(f"  Settlement:       {opt.best.settlement_mm:.2f} mm")
    print(f"  Estimated cost:   {opt.best.cost_eur:,.0f} EUR")
    print(f"  Passes all:       {opt.best.passes}")

    # --------------- 1bis. PDF report of the optimum ------------------
    pad = RectangularFoundation(
        length=opt.best.L * 1000.0, width=opt.best.B * 1000.0,
        thickness=opt.best.t * 1000.0, embedment_depth=1500.0,
    )
    q = 1500.0 / (opt.best.B * opt.best.L)
    res = design_footing_from_cpt(
        _cpt(), pad, founding_depth_m=1.5, q_applied_kPa=q,
        design_approach=DesignApproach.DA2, settlement_limit_mm=50.0,
    )
    report_path = report_cpt_to_design(
        _cpt(), pad, res, "out/cpt_optimum_report.pdf",
        meta=ReportMeta(
            project="CPT-based footing optimization",
            engineer="J. Murga", client="Demo Client",
            job_code="OPT-2026-01",
        ),
    )
    print(f"  PDF report:       {report_path}  ({os.path.getsize(report_path):,} bytes)")

    # --------------- 2. Pile group ------------------------------------
    print()
    print("--- Part 2: pile group 2 x 3, s = 2.4 m, d = 0.8 m ---")
    grp = rectangular_group(
        n_rows=2, n_cols=3, spacing_m=2.4, diameter_m=0.8,
        axial_capacity_kN=1500, tension_capacity_kN=400,
        lateral_capacity_kN=120,
    )
    print(f"  n_piles = {grp.n}")
    print(f"  s / d = {2.4 / 0.8:.1f}")
    print(f"  E_axial  (Converse-Labarre) = {grp.axial_efficiency():.3f}")
    print(f"  E_lateral (Mokwa-Duncan)    = {grp.lateral_efficiency():.3f}")
    res_g = distribute_loads_rigid_cap(
        grp, V_kN=6000, H_x_kN=0, H_y_kN=600,
        M_x_kNm=2000, M_y_kNm=0,
    )
    print()
    print(f"  Loads: V = 6000 kN, H_y = 600 kN, M_x = 2000 kN.m")
    print(f"  N_max compression = {res_g.N_max_compression:.0f} kN")
    print(f"  N_max tension     = {res_g.N_max_tension:.0f} kN")
    print(f"  H_max per pile    = {res_g.H_max_per_pile:.0f} kN")
    _ga = res_g.group_axial_utilization
    print(f"  Group util (axial) = "
          f"{'NO EVALUADO' if _ga is None else format(_ga * 100, '.1f') + ' %'}")
    print(f"  Estado del grupo   = {res_g.status.value}")
    print(f"  Governing pile     = {res_g.governing_pile}")
    print(f"  All OK            = {res_g.all_ok}")
    print()
    print("  Per-pile forces:")
    print(f"  {'pile':<5}{'x [m]':>8}{'y [m]':>8}{'N [kN]':>10}"
          f"{'H [kN]':>10}{'util':>8}")
    for f in res_g.forces:
        H = (f.H_x_kN ** 2 + f.H_y_kN ** 2) ** 0.5
        _computed = [u for u in (f.axial_utilization, f.lateral_utilization)
                     if u is not None]
        util = max(_computed) if _computed else None
        _ut = "  N/EVAL" if util is None else f"{util * 100:>6.1f}%"
        print(f"  {f.pile_name:<5}{f.x_m:>+8.2f}{f.y_m:>+8.2f}"
              f"{f.N_kN:>10.0f}{H:>10.0f}{_ut:>8}")


if __name__ == "__main__":
    main()
