"""EC8 design spectrum + foundation impedance example.

Two flows:

1. EC8 — build a design spectrum for a Granada office building on
   ground type C (importance class II, q = 3.0). Print S_d(T) at a few
   periods.

2. SSI — compute the foundation impedance of a 3 x 3 m footing on
   medium dense sand (G = 40 MPa, nu = 0.30) at f = 2 Hz. Print the
   6-DOF spring set ready to be exported to a dynamic solver.

Run with:   python -m examples.ec8_and_impedance_example
"""

from __future__ import annotations

from foundationcalc.codes.eurocode8 import (
    GroundType, ImportanceClass, build_design_spectrum,
)
from foundationcalc.dynamics import (
    rectangular_footing_impedance, soil_dynamic_modulus,
)


def main() -> None:
    # ---------------- 1. EC8 spectrum -----------------------------
    print("=" * 78)
    print("FoundationCalc - EC8-1 spectrum")
    print("=" * 78)
    ds = build_design_spectrum(
        country="ES", region="Granada",
        ground_type=GroundType.C,
        importance_class=ImportanceClass.II,
        behaviour_factor_q=3.0,
    )
    print(f"Site: {ds.country} / {ds.region}")
    print(f"  a_gR = {ds.a_gR_g:.3f} g,  gamma_I = {ds.gamma_I},  a_g = {ds.a_g_g:.3f}")
    print(f"  Spectrum type {ds.spectrum_type.value},  Ground {ds.ground_type.value}")
    print(f"  S = {ds.spectrum_params.S},  T_B = {ds.spectrum_params.T_B} s,  "
          f"T_C = {ds.spectrum_params.T_C} s,  T_D = {ds.spectrum_params.T_D} s")
    print()
    print(f"  {'T [s]':<8}{'S_e/g':<10}{'S_d/g':<10}")
    for T in [0.0, 0.05, 0.10, 0.20, 0.40, 0.60, 1.00, 1.50, 2.00, 3.00]:
        print(f"  {T:<8.2f}{ds.S_e(T):<10.4f}{ds.S_d(T):<10.4f}")

    # ---------------- 2. Foundation impedance ---------------------
    print()
    print("=" * 78)
    print("FoundationCalc - SSI / foundation impedance")
    print("=" * 78)
    p = soil_dynamic_modulus(E_static_MPa=30.0, nu=0.30, G_over_Gmax=0.4)
    print(f"E_static = 30 MPa, G/G_max = 0.4:")
    print(f"  G_max = {p['G_max_MPa']:.1f} MPa,  V_s = {p['V_s_m_s']:.0f} m/s")
    print()
    imp = rectangular_footing_impedance(
        B_m=3.0, L_m=3.0, G_MPa=p["G_max_MPa"],
        nu=0.30, frequency_Hz=2.0,
    )
    print(f"3 x 3 m footing, f = 2 Hz, V_s = {imp.V_s():.0f} m/s")
    print(f"  {'DOF':<14}{'K_static [kN/m]':<20}{'k_dyn':<10}{'c_dyn':<10}")
    for label, d in [
        ("vertical", imp.vertical),
        ("horizontal_x", imp.horizontal_x),
        ("horizontal_y", imp.horizontal_y),
        ("rocking_x", imp.rocking_x),
        ("rocking_y", imp.rocking_y),
        ("torsion", imp.torsion),
    ]:
        print(f"  {label:<14}{d.K_static:>18,.0f}  {d.k_dyn:<10.3f}{d.c_dyn:<10.3f}")

    print()
    print("Tip: launch the interactive dashboard with")
    print("  python -m foundationcalc.dashboard")


if __name__ == "__main__":
    main()
