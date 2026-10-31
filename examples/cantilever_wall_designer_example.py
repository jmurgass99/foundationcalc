"""End-to-end design of a cantilever retaining wall using the designer.

This complements `retaining_wall_example.py` (which exercises the
low-level earth-pressure helpers) by running the high-level
`CantileverWallDesigner` end-to-end across all 4 Design Approaches.

Setup (per metre run):
- 5.0 m high stem (30 cm top / 45 cm bottom thickness)
- 1.0 m toe + 2.5 m heel + 0.55 m base slab
- Compacted granular backfill: phi = 33 deg, gamma = 19 kN/m3
- Foundation: dense sand/gravel, phi = 36 deg, gamma = 20 kN/m3
- Uniform surcharge q = 10 kN/m2 (traffic)
- No water table
- Coulomb active pressure, delta = 2/3 phi on the virtual back

Run with:   python -m examples.cantilever_wall_designer_example
"""

from __future__ import annotations

from foundationcalc.codes.eurocode7 import DesignApproach
from foundationcalc.core.material import Concrete
from foundationcalc.core.soil import SoilLayer, SoilType
from foundationcalc.design.retaining_wall import (
    CantileverWallDesigner,
    CantileverWallGeometry,
    RetainingWallLoading,
)


def main() -> None:
    geo = CantileverWallGeometry(
        H=5.0,
        stem_top=0.30,
        stem_bottom=0.45,
        toe=1.0,
        heel=2.5,
        base_thickness=0.55,
        embedment_front=0.8,
    )
    backfill = SoilLayer(
        name="compacted_fill", thickness=10,
        soil_type=SoilType.COHESIONLESS,
        friction_angle=33, cohesion=0, unit_weight=19,
    )
    foundation = SoilLayer(
        name="gravel", thickness=10,
        soil_type=SoilType.COHESIONLESS,
        friction_angle=36, cohesion=0, unit_weight=20,
    )
    load = RetainingWallLoading(
        backfill=backfill,
        foundation_soil=foundation,
        surcharge_q=10.0,
        water_height=0.0,
        use_coulomb=True,
        delta_over_phi=2.0 / 3.0,
    )
    concrete = Concrete(name="C30/37", fck=30)

    print("=" * 78)
    print(f"FoundationCalc - Cantilever wall  H={geo.H}m  B={geo.B}m")
    print("=" * 78)
    print(f"Backfill: phi={backfill.friction_angle}deg, gamma={backfill.unit_weight} kN/m3")
    print(f"Foundation: phi={foundation.friction_angle}deg, gamma={foundation.unit_weight} kN/m3")
    print(f"Surcharge: {load.surcharge_q} kN/m2, water height: {load.water_height} m")
    print()

    for da in [DesignApproach.DA1_C1, DesignApproach.DA1_C2,
               DesignApproach.DA2, DesignApproach.DA3]:
        designer = CantileverWallDesigner(geo, load, concrete, design_approach=da)
        res = designer.check()
        verdict = "OK" if res.all_ok else "FAILS"
        print(f"[{da.value:<7}]  V={res.actions.V_d:>6.0f} kN/m  "
              f"H={res.actions.H_d:>5.0f} kN/m  "
              f"e_x={res.actions.e_x:>+6.3f} m  "
              f"middle-third={res.middle_third!s:<5}   {verdict}")
        print(f"           bearing:    q_Ed={res.bearing_q_Ed:>6.1f}  "
              f"q_Rd={res.bearing_q_Rd:>6.1f}  util={res.bearing_utilization*100:>5.1f}%")
        print(f"           sliding:    H_Ed={res.sliding_H_Ed:>6.1f}  "
              f"H_Rd={res.sliding_H_Rd:>6.1f}  util={res.sliding_utilization*100:>5.1f}%")
        print(f"           overturn:   M_dst={res.actions.M_dst:>6.0f}  "
              f"M_stb={res.actions.M_stb:>6.0f}  util={res.overturning_utilization*100:>5.1f}%")

    print()
    print("Structural critical-section forces (DA-2, per m run):")
    designer = CantileverWallDesigner(geo, load, concrete, design_approach=DesignApproach.DA2)
    res = designer.check()
    print(f"  STEM base:  M = {res.M_stem_base:>6.1f} kN.m/m   "
          f"V = {res.V_stem_base:>6.1f} kN/m")
    print(f"  HEEL:       M = {res.M_heel:>6.1f} kN.m/m   "
          f"V = {res.V_heel:>6.1f} kN/m")
    print(f"  TOE:        M = {res.M_toe:>6.1f} kN.m/m   "
          f"V = {res.V_toe:>6.1f} kN/m")


if __name__ == "__main__":
    main()
