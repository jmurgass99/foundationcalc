"""Cantilever retaining wall on clay - EC7 example (docs/theory/04 + 06)."""

import math

from foundationdesignjm.analysis.bearing_capacity import undrained_bearing_capacity
from foundationdesignjm.analysis.earth_pressure import (
    active_thrust,
    heel_min_width_for_rankine,
)
from foundationdesignjm.analysis.seismic import (
    mononobe_okabe_K,
    seismic_thrust,
)
from foundationdesignjm.analysis.stability import (
    overturning_check,
    sliding_resistance_undrained,
)
from foundationdesignjm.codes.eurocode7 import (
    DesignApproach,
    LimitState,
    get_partial_factors,
)
from foundationdesignjm.core.geometry import RectangularFoundation
from foundationdesignjm.core.soil import SoilLayer, SoilType


# --- Geometry & soils -----------------------------------------------------
H_fill = 3.0   # m, retained height
delta_H_unplanned = min(0.10 * H_fill, 0.5)
H_design = H_fill + delta_H_unplanned

B = 2.7
t_s = 0.25      # stem thickness
t_b = 0.30      # base thickness
x = 0.5         # toe length
d_below = 0.5   # base of wall below ground level
gamma_c = 25.0  # RC unit weight

# Fill on top of heel
fill = SoilLayer(
    name="sand fill", thickness=H_design + d_below,
    soil_type=SoilType.COHESIONLESS,
    friction_angle=36.0, cohesion=0.0, unit_weight=18.0,
)

# Foundation clay (under the wall)
clay = SoilLayer(
    name="clay", thickness=5.0, soil_type=SoilType.COHESIVE,
    undrained_shear_strength=45.0, unit_weight=22.0,
)

surcharge_q = 10.0  # variable surcharge on top of fill

# --- Self-weights ---------------------------------------------------------
W_base = gamma_c * B * t_b
W_stem = gamma_c * (H_fill + d_below - t_b) * t_s
b_heel = B - t_s - x
W_fill = fill.unit_weight * b_heel * (H_fill + d_below - t_b)
W_total = W_base + W_stem + W_fill

# Moments of self-weights about the toe (kN.m/m)
M_base = W_base * B / 2.0
M_stem = W_stem * (t_s / 2.0 + x)
M_fill = W_fill * (b_heel / 2.0 + t_s + x)
M_stb_char = M_base + M_stem + M_fill

print("=" * 70)
print("FoundationDesignJm - Cantilever wall on clay (undrained GEO)")
print("=" * 70)
print(f"H_design = {H_design:.2f} m, B = {B:.2f} m")
print(f"  b_heel = {b_heel:.2f} m, fill phi = {fill.friction_angle:.0f} deg")
print(f"  Clay c_u,k = {clay.undrained_shear_strength:.0f} kPa")
print(f"  W_total = {W_total:.1f} kN/m, M_stb,k = {M_stb_char:.1f} kN.m/m")
print()

# Heel-width check for Rankine validity
b_min = heel_min_width_for_rankine(H_design, fill.friction_angle)
print(f"Heel min for Rankine: {b_min:.2f} m  ({'OK' if b_heel >= b_min else 'NARROW - use Coulomb on virtual back'})")
print()


# --- Run all three Design Approaches --------------------------------------
for da in [DesignApproach.DA1_C1, DesignApproach.DA1_C2, DesignApproach.DA2, DesignApproach.DA3]:
    pf = get_partial_factors(da, LimitState.GEO)

    # Design fill parameters
    phi_d = math.degrees(math.atan(math.tan(math.radians(fill.friction_angle)) / pf.soil.gamma_phi))
    cu_d = clay.undrained_shear_strength / pf.soil.gamma_cu

    # Active thrust (Rankine)
    thrust_fill = active_thrust(
        H=H_design, gamma=fill.unit_weight,
        phi_deg=phi_d, c_prime=0.0,
        surcharge_q=surcharge_q,
    )
    H_Ed_unfactored = thrust_fill.thrust_P
    M_dst_unfactored = thrust_fill.overturning_moment

    # Factor up destabilising actions
    H_Ed = pf.actions.gamma_G_unfav * (0.5 * thrust_fill.coefficient_K * fill.unit_weight * H_design ** 2) \
        + pf.actions.gamma_Q_unfav * (thrust_fill.coefficient_K * surcharge_q * H_design)
    M_Ed_dst = pf.actions.gamma_G_unfav * (0.5 * thrust_fill.coefficient_K * fill.unit_weight * H_design ** 2 * H_design / 3.0) \
        + pf.actions.gamma_Q_unfav * (thrust_fill.coefficient_K * surcharge_q * H_design * H_design / 2.0)

    # Vertical load on the base (unfavourable for bearing)
    V_d = pf.actions.gamma_G_unfav * W_total + pf.actions.gamma_Q_unfav * (surcharge_q * b_heel)
    V_d_fav = pf.actions.gamma_G_fav * W_total

    # Stabilising moment about toe (for overturning)
    M_Ed_stb = pf.actions.gamma_G_unfav * M_stb_char \
        + pf.actions.gamma_Q_unfav * (surcharge_q * b_heel) * (b_heel / 2.0 + t_s + x)

    # Sliding (undrained)
    foundation = RectangularFoundation(
        length=10000.0, width=B * 1000.0, thickness=t_b * 1000.0, embedment_depth=d_below * 1000.0,
    )
    A_eff = B * 1.0  # per metre run
    sliding = sliding_resistance_undrained(
        N_Ed=V_d_fav, soil=clay, A_eff=A_eff, H_Ed=H_Ed,
        gamma_cu=pf.soil.gamma_cu, gamma_Rh=pf.resistance.gamma_Rh,
    )

    # Overturning
    overturn = overturning_check(M_dst_d=M_Ed_dst, M_stb_d=M_Ed_stb, V_d=V_d, B=B)

    # Bearing (undrained)
    bearing = undrained_bearing_capacity(
        foundation=foundation,
        soil=clay,
        e_x=overturn.e_B,
        gamma_Rv=pf.resistance.gamma_Rv,
        gamma_cu=pf.soil.gamma_cu,
    )
    q_Ed = V_d / max(B - 2 * abs(overturn.e_B), 1e-6)
    q_Rd = bearing.q_ult / pf.resistance.gamma_Rv

    print(f"--- {da.value} ---")
    print(f"  K_a              = {thrust_fill.coefficient_K:.3f}  (phi_d = {phi_d:.1f} deg)")
    print(f"  H_Ed             = {H_Ed:8.1f} kN/m")
    print(f"  V_d (unfav/fav)  = {V_d:6.1f} / {V_d_fav:6.1f} kN/m")
    print(f"  M_Ed,dst/stb     = {M_Ed_dst:6.1f} / {M_Ed_stb:6.1f} kN.m/m")
    print(f"  e_B              = {overturn.e_B:6.3f} m  (middle-third {'OK' if overturn.middle_third else 'NO'})")
    print(f"  Sliding   Lambda = {sliding.utilization * 100:5.1f} %")
    print(f"  Bearing   Lambda = {q_Ed / q_Rd * 100:5.1f} %  (q_Ed={q_Ed:.0f}, q_Rd={q_Rd:.0f} kPa)")
    print(f"  Toppling  Lambda = {overturn.utilization * 100:5.1f} %")
    print()


# --- Seismic comparison (Mononobe-Okabe) ----------------------------------
K_mo, theta = mononobe_okabe_K(
    phi_deg=36.0, delta_deg=2.0 / 3.0 * 36.0, psi_deg=90.0, beta_deg=0.0,
    kh=0.20, kv=0.0,
)
seismic = seismic_thrust(H=H_design, gamma_star=fill.unit_weight, K_mo=K_mo)
print(f"Seismic (M-O, k_h=0.20): K = {K_mo:.3f}, E_d = {seismic.seismic_thrust:.1f} kN/m")
