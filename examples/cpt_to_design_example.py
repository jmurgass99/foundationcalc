"""End-to-end footing design from a CPT log.

Demonstrates the full pipeline:
  CPT log -> stratification -> soil profile -> multi-layer bearing capacity
       + failure-mode classification + integrated settlement -> verdict.

The CPT log represents a typical Mediterranean coastal site:
  - 0-3 m: medium sand fill (q_c = 6 MPa)
  - 3-7 m: soft normally-consolidated marine clay (q_c = 1.2 MPa)
  - 7-15 m: dense sand (q_c = 18 MPa)
  - Water table at 2.5 m below surface

A 2.5 x 2.5 m footing founded at 1.5 m, carrying q = 180 kPa, is tested.

Run with:   python -m examples.cpt_to_design_example
"""

from __future__ import annotations

from foundationcalc.analysis.cpt import CPTProfile, CPTReading
from foundationcalc.analysis.cpt_to_design import design_footing_from_cpt
from foundationcalc.codes.eurocode7 import DesignApproach
from foundationcalc.core.geometry import RectangularFoundation


def _build_cpt() -> CPTProfile:
    readings = []
    # 0-3 m medium sand
    for d in [0.5, 1, 1.5, 2, 2.5, 3]:
        readings.append(CPTReading(depth=d, q_c_MPa=6.0, f_s_kPa=40))
    # 3-7 m soft clay (below water table)
    for d in [3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7]:
        readings.append(CPTReading(depth=d, q_c_MPa=1.2, f_s_kPa=60, u_2_kPa=60))
    # 7-15 m dense sand
    for d in [7.5, 8, 9, 10, 11, 12, 13, 14, 15]:
        readings.append(CPTReading(depth=d, q_c_MPa=18.0, f_s_kPa=80))
    return CPTProfile(
        readings=readings, water_table_depth_m=2.5,
        gamma_above_wt_kN_m3=18, gamma_below_wt_kN_m3=20,
    )


def main() -> None:
    cpt = _build_cpt()
    pad = RectangularFoundation(
        length=2500, width=2500, thickness=500, embedment_depth=1500,
    )

    print("=" * 78)
    print("FoundationCalc - End-to-end footing design from CPT data")
    print("=" * 78)
    print(f"CPT log:       {len(cpt.readings)} readings, depth 0.5 - 15 m, WT at 2.5 m")
    print(f"Footing:       {pad.width_m} x {pad.length_m} m, founded at 1.5 m")
    print(f"Applied:       q = 180 kPa (ULS)")
    print()

    for da in [DesignApproach.DA1_C1, DesignApproach.DA1_C2,
               DesignApproach.DA2, DesignApproach.DA3]:
        res = design_footing_from_cpt(
            cpt, pad, founding_depth_m=1.5, q_applied_kPa=180,
            design_approach=da, n_strata=5, settlement_limit_mm=50.0,
        )
        print(f"--- {da.value} ---")
        print(f"  Bearing  q_Ed = {res.q_applied_kPa:>6.1f}   "
              f"q_Rd = {res.q_Rd_kPa:>6.1f}   "
              f"util = {res.bearing_utilization*100:>5.1f}%   "
              f"{'OK' if res.bearing_ok else 'FAIL'}")
        print(f"  Governing case: {res.bearing.governing_case}  -> {res.bearing.governing_layer}")
        print(f"  Failure mode:   {res.failure_mode.mode.value}  "
              f"(I_r = {res.failure_mode.I_r:.0f}, I_rc = {res.failure_mode.I_rc:.0f})")
        print(f"  Settlement: imm = {res.settlement.s_immediate_mm:>5.1f} mm,  "
              f"cons = {res.settlement.s_consolidation_mm:>6.1f} mm,  "
              f"TOTAL = {res.settlement.s_total_mm:>6.1f} mm   "
              f"{'OK' if res.settlement_ok else 'EXCEEDS ' + str(int(res.settlement_limit_mm)) + ' mm'}")
        print()

    # Auto-derived soil profile
    print("Auto-derived soil profile from CPT:")
    res = design_footing_from_cpt(
        cpt, pad, founding_depth_m=1.5, q_applied_kPa=180,
        design_approach=DesignApproach.DA2,
    )
    for L in res.profile.layers:
        fields = []
        if L.friction_angle:
            fields.append(f"phi = {L.friction_angle:.1f} deg")
        if L.undrained_shear_strength:
            fields.append(f"c_u = {L.undrained_shear_strength:.0f} kPa")
        if L.youngs_modulus:
            fields.append(f"E = {L.youngs_modulus:.0f} MPa")
        print(f"  {L.name:<30} {L.soil_type.value:<14}  t = {L.thickness:.2f} m  "
              f"{'  '.join(fields)}")


if __name__ == "__main__":
    main()
