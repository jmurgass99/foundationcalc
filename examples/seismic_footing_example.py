"""Seismic verification of a spread footing per EN 1998-5.

Scenario: 3.0 x 3.0 x 0.7 m pad founded 1.2 m below grade, supporting
a column in a 5-storey RC building in moderate-seismicity Spain
(a_g = 0.20 g, ground type C → S = 1.15).

Seismic combination at the column base (EC0 + EC8):
- G_k    = 900 kN (permanent)
- 0.3 Q_k = 90 kN
- E       = ± horizontal acceleration on the structure → V = 180 kN, M = 420 kN.m
Total N = 1200 kN (G + 0.3 Q + extra)

The script prints the EN 1998-5 §5.4 verification across:
  - bearing capacity with seismic reduction
  - sliding (column shear + foundation block inertia)
  - overturning
"""

from __future__ import annotations

from foundationcalc.analysis.seismic_footing import (
    SeismicAction,
    seismic_footing_check,
)
from foundationcalc.codes.eurocode7 import DesignApproach
from foundationcalc.core.geometry import Column, RectangularFoundation
from foundationcalc.core.material import Concrete
from foundationcalc.core.soil import SoilLayer, SoilType


def main() -> None:
    pad = RectangularFoundation(length=3000, width=3000, thickness=700,
                                embedment_depth=1200)
    col = Column(length=400, width=400, pos_x=1500, pos_y=1500)
    soil = SoilLayer(
        name="dense_sand", thickness=10, soil_type=SoilType.COHESIONLESS,
        friction_angle=36, cohesion=0, unit_weight=20,
    )
    concrete = Concrete(name="C30/37", fck=30)
    seism = SeismicAction(
        a_g=0.20, S=1.15, importance_factor_gamma_I=1.0, r_factor=2.0,
    )
    print("=" * 78)
    print(f"FoundationCalc - Seismic footing 3.0 x 3.0 x 0.7 m")
    print("=" * 78)
    print(f"a_g = {seism.a_g}, S = {seism.S}, gamma_I = {seism.importance_factor_gamma_I}")
    print(f"k_h = {seism.k_h:.3f},  k_v (up) = {seism.k_v_up:.3f}")
    print()

    cases = [
        ("Strong shaking",   {"N": 1200, "H": 180, "M": 420}),
        ("Moderate shaking", {"N": 1200, "H": 120, "M": 280}),
        ("No earthquake (G+0.3Q)", {"N": 1200, "H": 0, "M": 0}),
    ]

    for label, loads in cases:
        print(f"--- {label} ---")
        for da in [DesignApproach.DA1_C1, DesignApproach.DA2, DesignApproach.DA3]:
            res = seismic_footing_check(
                pad, col,
                N_kN=loads["N"], H_kN=loads["H"], M_kNm=loads["M"],
                soil=soil, concrete=concrete, seismic=seism,
                design_approach=da, drained=True,
                soil_overburden_depth_mm=500, soil_unit_weight_overburden=18,
            )
            verdict = "OK" if res.all_ok else "FAILS"
            print(f"  [{da.value:<7}]  N={res.N_d:>5.0f}  H={res.H_d:>5.0f}  M={res.M_d:>5.0f}  "
                  f"e_y={res.e_y:>+6.3f}m  "
                  f"bear={res.bearing_utilization*100:>5.1f}%  "
                  f"slid={res.sliding_utilization*100:>5.1f}%  "
                  f"over={res.overturning_utilization*100:>5.1f}%   {verdict}")
        print()


if __name__ == "__main__":
    main()
