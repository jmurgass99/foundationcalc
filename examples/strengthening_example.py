"""Strengthening of an existing foundation — three intervention scenarios.

Existing situation: an old isolated footing 2.0 x 2.0 x 0.5 m supports
a column with current N = 900 kN (G + Q). A change of use brings the new
column load to N_new = 1 600 kN. The existing soil bearing pressure
limit is 220 kPa. Two foundation reference points A and B that were 6 m
apart show 12 mm differential settlement.

The script runs three interventions:
  1. Damage / SLS distortion check.
  2. Footing enlargement to 3.5 x 3.5 m (RC ring jacket).
  3. Underpinning with 6 micropiles 0.20 m drilling diameter through
     the original footing.

Run with:   python -m examples.strengthening_example
"""

from __future__ import annotations

from foundationdesignjm.design.strengthening import (
    MicropileGeometry,
    MicropileSoilType,
    StructureType,
    UnderpinningPit,
    angular_distortion_check,
    enlarged_footing_pressure,
    mass_concrete_underpinning,
    micropile_capacity,
    micropile_group_capacity,
)


def main() -> None:
    print("=" * 78)
    print("FoundationDesignJm - Strengthening of an existing footing")
    print("=" * 78)

    # ----- 1. Damage assessment ------------------------------------------
    print("\n[1] Angular distortion vs CTE limits")
    for st in [
        StructureType.FRAME_WITH_PARTITIONS,
        StructureType.UNREINFORCED_MASONRY_SAGGING,
        StructureType.UNREINFORCED_MASONRY_HOGGING,
    ]:
        r = angular_distortion_check(
            delta_s_AB_mm=12.0, L_AB_m=6.0, structure_type=st,
        )
        print(f"   {st.value:<22}  beta={r.beta*1000:>6.3f} permille  "
              f"limit={r.beta_limit*1000:>6.3f}  util={r.utilization*100:>5.1f}%  "
              f"{'OK' if r.ok else 'FAILS'}")

    # ----- 2. Footing enlargement ----------------------------------------
    print("\n[2] Enlarging 2.0 x 2.0 m -> 3.5 x 3.5 m for new N = 1 600 kN")
    r = enlarged_footing_pressure(
        N_kN=1600.0, A_old_m2=2.0 * 2.0,
        new_width_m=3.5, new_length_m=3.5,
    )
    print(f"   A_old = {r.A_old:.2f} m2,  A_new = {r.A_new:.2f} m2")
    print(f"   q_old = {r.q_old:.1f} kPa (would be 400 kPa - exceeds 220)")
    print(f"   q_new = {r.q_new:.1f} kPa  reduction = {r.reduction_pct:.1f} %")
    print(f"   Interface shear required = {r.interface_shear_required:.1f} kPa")

    # ----- 3. Mass-concrete underpinning of a strip foundation ----------
    print("\n[3] Mass-concrete underpinning of a 12 m masonry wall "
          "(80 kN/m, 220 kPa soil)")
    pit = UnderpinningPit(width=0.9, depth_below_old=1.2, along_wall_length=1.0)
    r = mass_concrete_underpinning(
        wall_load_kN_per_m=80.0, wall_length_m=12.0,
        pit=pit, q_allow_kPa=220.0,
    )
    print(f"   {r.n_pits} pits of {pit.width} x {pit.along_wall_length} m")
    print(f"   N per pit = {r.N_per_pit:.1f} kN")
    print(f"   q_deepened = {r.q_deepened:.1f} kPa  (allow {r.q_allow:.0f} kPa)  "
          f"util = {r.utilization*100:.1f}%  {'OK' if r.ok else 'FAILS'}")
    print(f"   Stage pattern: {r.stage_pattern}")

    # ----- 4. Micropile underpinning ------------------------------------
    print("\n[4] Underpinning with 6 micropiles, d_drill=0.20, L_bond=8 m, "
          "sand and gravel")
    geom = MicropileGeometry(
        diameter_drilling=0.20, diameter_grouted=0.24,
        length_total=12.0, length_bond=8.0,
    )
    cap = micropile_capacity(
        geom, MicropileSoilType.SAND_GRAVEL,
        q_s_kPa=120.0,           # IRS injection upper-mid range
        correlation_factor_xi=1.30,
        gamma_R_total=1.50,
        alpha_inj=1.20,
    )
    print(f"   q_s used = {cap.q_s_used:.0f} kPa  "
          f"R_skin,char = {cap.R_skin_char:.0f} kN  "
          f"R_skin,d = {cap.R_skin_design:.0f} kN")
    group = micropile_group_capacity(
        n_piles=6, R_per_pile_design_kN=cap.R_total_design,
        spacing_to_diameter=3.5,  # s/d = 3.5 → fully efficient
        N_design_kN=1600.0,
    )
    print(f"   Group: {group.n_piles} piles, E = {group.efficiency_E:.2f},  "
          f"R_group,d = {group.R_group_design:.0f} kN")
    print(f"   util = {group.utilization*100:.1f}%  "
          f"{'OK' if group.ok else 'FAILS'}")


if __name__ == "__main__":
    main()
