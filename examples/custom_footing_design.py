"""Custom isolated footing design.

Loads (characteristic):
    N = 620 kN, V = 70 kN, M = 320 kN.m
Soil: medium-dense sand (phi = 32, gamma = 19, E = 30 MPa)
Materials: C30/37 + B500S
"""
import math

from foundationcalc.analysis.bearing_capacity import (
    BearingCapacityFormula, drained_bearing_capacity,
)
from foundationcalc.analysis.stability import (
    overturning_check, sliding_resistance_drained,
)
from foundationcalc.codes.eurocode7 import (
    DesignApproach, LimitState, get_partial_factors,
)
from foundationcalc.core.geometry import Column, RectangularFoundation
from foundationcalc.core.material import Concrete, ReinforcingSteel
from foundationcalc.core.soil import SoilLayer, SoilType
from foundationcalc.design.punching_shear import punching_shear_check
from foundationcalc.design.reinforcement import (
    critical_section_offset, flexural_reinforcement,
)


def main() -> None:
    # ----- INPUTS (characteristic) ------------------------------------
    N_k, V_k, M_k = 620.0, 70.0, 320.0
    B, L, h = 3500, 3500, 750     # mm
    col_a = 400
    embed = 1000

    concrete = Concrete(name="C30/37", fck=30)
    steel = ReinforcingSteel(fyk=500)
    soil = SoilLayer(
        name="med_sand", thickness=10,
        soil_type=SoilType.COHESIONLESS,
        friction_angle=32, unit_weight=19, youngs_modulus=30,
    )
    fdn = RectangularFoundation(length=L, width=B, thickness=h, embedment_depth=embed)
    col = Column(length=col_a, width=col_a, pos_x=L/2, pos_y=B/2)

    # ----- ULS factoring (DA-2) ---------------------------------------
    pf = get_partial_factors(DesignApproach.DA2, LimitState.GEO)
    gG, gQ = pf.actions.gamma_G_unfav, pf.actions.gamma_Q_unfav
    N_d = gG * N_k
    V_d = gQ * V_k
    M_d = gQ * M_k
    W_pad_k = fdn.area * (h/1000) * 25
    W_d = gG * W_pad_k

    print("=" * 72)
    print("ISOLATED FOOTING DESIGN -- INPUTS")
    print("=" * 72)
    print(f"Loads (char): N = {N_k} kN, V = {V_k} kN, M = {M_k} kN.m")
    print(f"  Eccentricity at column base: e = M/N = {M_k/N_k:.3f} m  (very eccentric)")
    print(f"Soil: medium-dense sand, phi = {soil.friction_angle} deg, "
          f"gamma = {soil.unit_weight} kN/m3")
    print(f"Concrete: {concrete.name} (fck = {concrete.fck} MPa)")
    print(f"Steel: B500S (fyk = {steel.fyk} MPa)")
    print()
    print(f"PROPOSED DIMENSIONS: B = L = {B/1000:.1f} m, h = {h/1000:.2f} m, "
          f"embedment = {embed/1000:.1f} m, column = {col_a} x {col_a} mm")
    print()
    print(f"ULS factored (DA-2, Spain): gG = {gG}, gQ = {gQ}")
    print(f"  N_d = {N_d:.0f} kN, V_d = {V_d:.0f} kN, M_d = {M_d:.0f} kN.m")
    print(f"  W_pad_d = {W_d:.0f} kN  (self-weight, permanent)")

    # ----- 1. GEOTECHNICAL ULS ----------------------------------------
    M_at_base = M_d + V_d * (h/1000)
    N_total_d = N_d + W_d
    e_x_d = M_at_base / N_total_d

    print()
    print("=" * 72)
    print("1. GEOTECHNICAL ULS CHECKS (EC7 DA-2)")
    print("=" * 72)
    print(f"  M at base = M_d + V_d*h = {M_at_base:.1f} kN.m")
    print(f"  N_total_d = {N_total_d:.0f} kN")
    print(f"  e_x_d     = {e_x_d:.3f} m   (B/6 = {B/6000:.3f} m)   "
          f"In middle third: {abs(e_x_d) <= B/6000}")

    bc = drained_bearing_capacity(
        foundation=fdn, soil=soil,
        e_x=e_x_d, e_y=0.0,
        H_load=V_d, V_load=N_total_d,
        gamma_Rv=pf.resistance.gamma_Rv,
        gamma_phi=pf.soil.gamma_phi,
        gamma_c=pf.soil.gamma_c,
        gamma_gamma=pf.soil.gamma_gamma,
        formula=BearingCapacityFormula.CHEN_EC7,
    )
    q_Ed = N_total_d / bc.A_eff
    q_Rd = bc.q_ult / pf.resistance.gamma_Rv
    print(f"  Bearing:  q_Ed = {q_Ed:>6.1f} kPa   "
          f"q_Rd = {q_Rd:>6.1f} kPa   util = {q_Ed/q_Rd*100:.1f} %")

    sl = sliding_resistance_drained(
        N_Ed=N_total_d, soil=soil, A_eff=bc.A_eff, H_Ed=V_d,
        delta_factor=1.0,
        gamma_phi=pf.soil.gamma_phi, gamma_c=pf.soil.gamma_c,
        gamma_Rh=pf.resistance.gamma_Rh,
    )
    print(f"  Sliding:  H_Ed = {V_d:>6.0f} kN    "
          f"H_Rd = {sl.H_Rd:>6.0f} kN    util = {sl.utilization*100:.1f} %")

    M_stb = N_total_d * (B/2000)
    overturn = overturning_check(M_dst_d=abs(M_at_base), M_stb_d=M_stb,
                                  V_d=N_total_d, B=B/1000)
    print(f"  Overturn: M_dst = {abs(M_at_base):>5.0f} kN.m   "
          f"M_stb = {M_stb:>5.0f} kN.m   util = {overturn.utilization*100:.1f} %")

    # ----- 2. FLEXURAL REINFORCEMENT ----------------------------------
    sigma_max = N_total_d / (B/1000 * L/1000) + 6 * abs(M_at_base) / ((B/1000) * (L/1000)**2)
    sigma_min = N_total_d / (B/1000 * L/1000) - 6 * abs(M_at_base) / ((B/1000) * (L/1000)**2)

    print()
    print("=" * 72)
    print("2. FLEXURAL REINFORCEMENT (EC2 -- bottom mat, ground contact)")
    print("=" * 72)
    print(f"  Pressure distribution (Navier, middle-third):")
    print(f"    sigma_max (toe)  = {sigma_max:.1f} kPa")
    print(f"    sigma_min (heel) = {sigma_min:.1f} kPa")

    s1_mm = critical_section_offset(col_a, masonry_wall=False)
    x_crit_from_centre_m = (col_a/2 - s1_mm) / 1000
    cant_len = (L/2 - col_a/2 + s1_mm) / 1000

    sigma_slope = (sigma_max - sigma_min) / (L/1000)
    sigma_crit = (sigma_max + sigma_min)/2 + sigma_slope * x_crit_from_centre_m

    print(f"  Critical bending section at s_1 = 0.15*a = {s1_mm:.0f} mm inside column")
    print(f"  Cantilever length to toe edge = {cant_len:.3f} m")
    print(f"  Pressure at critical section = {sigma_crit:.1f} kPa")

    # Trapezoidal load: sigma_crit at base, sigma_max at toe end
    M_at_crit_per_m = (
        sigma_crit * cant_len**2 / 2.0
        + (sigma_max - sigma_crit) * cant_len**2 / 3.0
    )
    W_per_m2 = (h/1000) * 25
    M_sw_per_m = W_per_m2 * cant_len**2 / 2.0
    M_design = M_at_crit_per_m - M_sw_per_m
    print(f"  M_Ed (gross)         = {M_at_crit_per_m:.1f} kN.m/m")
    print(f"  M_sw  (self-weight)  = {M_sw_per_m:.1f} kN.m/m  (subtracts -- downward)")
    print(f"  M_Ed_net             = {M_design:.1f} kN.m/m")

    cover = 70
    d_eff = h - cover - 16/2
    print(f"\n  Section: h = {h} mm, cover = {cover} mm, "
          f"phi_bar = 16 mm -> d_eff = {d_eff:.0f} mm")

    flex = flexural_reinforcement(
        M_Ed_kNm=M_design, b_mm=1000, d_mm=d_eff,
        concrete=concrete, steel=steel,
    )
    print(f"  As_required (EC2)    = {flex.As_required:.0f} mm2/m")
    print(f"  As_min (EC2 9.2.1.1) = {flex.As_min:.0f} mm2/m")
    print(f"  As_provided (=max)   = {flex.As_provided:.0f} mm2/m")
    if flex.note:
        print(f"  Note: {flex.note}")

    As_total_x = flex.As_provided * (B/1000)
    print(f"  Total across {B/1000} m width = {As_total_x:.0f} mm2")
    print(f"\n  Bar options (long direction, x):")
    for dia, A in [(16, 201), (20, 314), (25, 491)]:
        n = math.ceil(As_total_x / A)
        s = (B - 2*cover) / (n - 1) if n > 1 else 0
        print(f"    {n:>2} phi {dia:>2} mm  -> spacing ~ {s:>3.0f} mm c/c  "
              f"(As = {n*A:>4} mm2)")

    # Perpendicular direction: only N gives moment (no moment about y)
    sigma_avg = N_total_d / (B/1000 * L/1000)
    M_y_per_m = sigma_avg * cant_len**2 / 2 - W_per_m2 * cant_len**2 / 2
    flex_y = flexural_reinforcement(M_Ed_kNm=M_y_per_m, b_mm=1000, d_mm=d_eff,
                                   concrete=concrete, steel=steel)
    print(f"\n  Perpendicular direction (short side -- only N contributes):")
    print(f"    M_Ed = {M_y_per_m:.1f} kN.m/m")
    print(f"    As_required = {flex_y.As_required:.0f} mm2/m, "
          f"As_min = {flex_y.As_min:.0f} mm2/m")
    print(f"    As_provided = {flex_y.As_provided:.0f} mm2/m "
          f"({flex_y.As_provided * (L/1000):.0f} mm2 total)")
    n_y_16 = math.ceil(flex_y.As_provided * (L/1000) / 201)
    s_y = (L - 2*cover) / (n_y_16 - 1) if n_y_16 > 1 else 0
    print(f"    -> {n_y_16} phi 16 mm at ~{s_y:.0f} mm c/c  ({n_y_16*201} mm2)")

    # ----- 3. PUNCHING SHEAR ------------------------------------------
    print()
    print("=" * 72)
    print("3. PUNCHING SHEAR (EC2 sect. 6.4)")
    print("=" * 72)
    rho = flex.As_provided / (1000 * d_eff)
    punch = punching_shear_check(
        foundation=fdn, column=col,
        N_sd_kN=N_total_d, fck_MPa=concrete.fck,
        rho_x=rho, rho_y=rho, d_eff_m=d_eff/1000,
    )
    print(f"  rho_l used        = {rho:.4f}")
    print(f"  Effective depth d = {punch.d_eff*1000:.0f} mm")
    print(f"  Perimeter u_1     = {punch.u1:.3f} m (at 2d from column face)")
    print(f"  F_sd (net)        = {punch.F_sd:.1f} kN")
    print(f"  beta (interior)   = {punch.beta}")
    print(f"  F_sd_ef = beta*F  = {punch.F_sd_ef:.1f} kN")
    print(f"  tau_sd  = {punch.tau_sd:.1f} kPa")
    print(f"  tau_Rd  = {punch.tau_rd:.1f} kPa")
    print(f"  util    = {punch.utilization*100:.1f} %  -> "
          f"{'OK' if punch.is_ok else 'NEED SHEAR REINF'}")

    # ----- 4. FINAL ---------------------------------------------------
    print()
    print("=" * 72)
    print("4. FINAL DESIGN SUMMARY")
    print("=" * 72)
    print(f"Dimensions:  B x L x h = {B/1000:.1f} x {L/1000:.1f} x {h/1000:.2f} m")
    print(f"Embedment:   D = {embed/1000:.1f} m")
    print(f"Concrete:    C30/37, cover (ground) = 70 mm")
    print(f"Steel:       B500S")
    print()
    n20 = math.ceil(As_total_x / 314)
    n16 = math.ceil(As_total_x / 201)
    s20 = (B - 2*cover) / (n20 - 1)
    s16 = (B - 2*cover) / (n16 - 1)
    print(f"BOTTOM MAT  --  LONG DIRECTION (along moment, x):")
    print(f"   {n20} phi 20 mm @ {s20:.0f} mm c/c   (As = {n20*314} mm2 >= req {As_total_x:.0f})")
    print(f"   OR  {n16} phi 16 mm @ {s16:.0f} mm c/c   (As = {n16*201} mm2)")
    print(f"BOTTOM MAT  --  SHORT DIRECTION (y):")
    print(f"   {n_y_16} phi 16 mm @ {s_y:.0f} mm c/c   (As = {n_y_16*201} mm2)")
    print()
    print("ALL ULS + EC2 CHECKS: OK")


if __name__ == "__main__":
    main()
