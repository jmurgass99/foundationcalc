"""Correcciones de la 1.1.0, cada una con su oráculo (a mano o método independiente).

Cada test nombra el defecto que fija; el CHANGELOG da el impacto numérico.
"""
from __future__ import annotations

import math
import tomllib
from pathlib import Path

import numpy as np
import pytest

from foundationcalc.analysis.consolidation import elastic_settlement_rectangle
from foundationcalc.analysis.earth_pressure import Ka_rankine, Ka_rankine_inclined, passive_thrust
from foundationcalc.analysis.pile_capacity import pile_axial_capacity
from foundationcalc.analysis.seismic import liquefaction_screening, seismic_thrust
from foundationcalc.analysis.stress import (
    boussinesq_line_load_dsigma_z,
    boussinesq_strip_load_dsigma_z,
)
from foundationcalc.analysis.winkler import FootingGeometry, SoilLayer as DynSoil, gazetas_stiffness
from foundationcalc.codes.aci318_anchorage import shear_capacity
from foundationcalc.codes.eurocode7 import DesignApproach, LimitState, get_partial_factors
from foundationcalc.core.geometry import Column, RectangularFoundation
from foundationcalc.core.material import Concrete
from foundationcalc.core.piles import Pile
from foundationcalc.core.soil import SoilLayer, SoilProfile, SoilType
from foundationcalc.design.punching_shear import punching_shear_check
from foundationcalc.dynamics import rectangular_footing_impedance

# ---------------------------------------------------------------------------
# Tensiones y asientos
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("x", [0.0, 0.5, 1.0, 2.0])
def test_strip_load_matches_numerical_integration_of_line_loads(x):
    """Faja flexible B = 2 m, q = 100 kPa, z = 2 m.

    Oráculo independiente: la faja es la integral de cargas lineales
    Δσ = 2·q·dξ·z³/(π·((x−ξ)² + z²)²), integrada con 20 000 franjas. Antes de la
    1.1.0 el eje daba 44,8 kPa (0,448·q) en vez de 55,0 kPa (0,550·q de las
    tablas de Das para z/b = 2) y el borde 25,0 en vez de 40,9 kPa.
    """
    q, B, z = 100.0, 2.0, 2.0
    n = 20000
    xi = -B / 2 + (np.arange(n) + 0.5) * B / n
    numeric = sum(boussinesq_line_load_dsigma_z(q * B / n, x - s, z) for s in xi)
    assert boussinesq_strip_load_dsigma_z(q, B, x, z) == pytest.approx(numeric, rel=1e-6)


def test_strip_load_centre_table_value():
    # Das, tabla de la faja: z/b = 2 (b = B/2) bajo el eje -> 0,550·q.
    assert boussinesq_strip_load_dsigma_z(100.0, 2.0, 0.0, 2.0) == pytest.approx(55.0, abs=0.05)


def _I_corner_numeric(L_over_B: float, m: int = 400) -> float:
    """I = (1/(π·B))·∬ dA / r sobre el rectángulo, desde la esquina (B = 1)."""
    x = (np.arange(m) + 0.5) / m
    y = (np.arange(m) + 0.5) * L_over_B / m
    X, Y = np.meshgrid(x, y)
    return float(np.sum(1.0 / np.hypot(X, Y)) * (1.0 / m) * (L_over_B / m) / math.pi)


@pytest.mark.parametrize("LB", [1.0, 2.0, 5.0])
def test_elastic_settlement_influence_factor_corner_and_centre(LB):
    """s = q·B·(1−ν²)/E·I_s. Oráculo: integración numérica de Boussinesq.

    Antes, L/B = 2 daba I = 2,14 (centro real 1,53) y L/B = 5, 7,49 (2,10).
    """
    I_c = _I_corner_numeric(LB)
    s_corner = elastic_settlement_rectangle(1.0, 1.0, LB, 1.0, nu=0.0, location="corner")
    s_centre = elastic_settlement_rectangle(1.0, 1.0, LB, 1.0, nu=0.0)
    assert s_corner == pytest.approx(I_c, rel=5e-3)
    assert s_centre == pytest.approx(2.0 * I_c, rel=5e-3)


def test_elastic_settlement_square_table_values():
    # Zapata cuadrada flexible: 1,12 en el centro y 0,56 en la esquina.
    assert elastic_settlement_rectangle(1.0, 1.0, 1.0, 1.0, nu=0.0) == pytest.approx(1.122, abs=1e-3)
    assert elastic_settlement_rectangle(1.0, 1.0, 1.0, 1.0, nu=0.0, location="corner") == pytest.approx(0.561, abs=1e-3)


# ---------------------------------------------------------------------------
# Resortes de Gazetas (NIST GCR 12-917-21, Tabla 2-2a; L y B semidimensiones)
# ---------------------------------------------------------------------------
#   Zapata 2 × 2 m -> L = B = 1 m; G = 1900·200² = 76 MPa; ν = 0,35
#   Kz  = 2·76000·1/0,65·(0,73 + 1,54)          = 530 830,77 kN/m
#   Ky  = 2·76000·1/1,65·(2 + 2,5)              = 414 545,45 kN/m  (= Kx en cuadrada)
#   I   = 2·2³/12 = 1,33333 m⁴ -> I^0,75 = 1,240806
#   Krx = 76000/0,65·1,240806·(2,4 + 0,5)       = 420 728,84 kN·m/rad
#   Kry = 76000/0,65·1,240806·3                 = 435 236,73 kN·m/rad
#   Krz = 76000·(2,66667)^0,75·(4 + 0)          = 634 380,95 kN·m/rad
G_KPA = 76000.0
EXPECTED = {"Kz": 530830.77, "Ky": 414545.45, "Krx": 420728.84, "Kry": 435236.73, "Krz": 634380.95}


def test_gazetas_winkler_uses_half_dimensions():
    k = gazetas_stiffness(FootingGeometry(L=2.0, B=2.0), DynSoil(thickness=10.0, Vs=200.0, rho=1900.0, nu=0.35))
    assert k.Kz / 1000 == pytest.approx(EXPECTED["Kz"], rel=1e-6)   # antes 1 061 662 (×2)
    assert k.Ky / 1000 == pytest.approx(EXPECTED["Ky"], rel=1e-6)
    assert k.Kx / 1000 == pytest.approx(EXPECTED["Ky"], rel=1e-6)
    assert k.Krx / 1000 == pytest.approx(EXPECTED["Krx"], rel=1e-6)
    assert k.Kry / 1000 == pytest.approx(EXPECTED["Kry"], rel=1e-6)  # antes 507 776 (3,5 en vez de 3)
    assert k.Krz / 1000 == pytest.approx(EXPECTED["Krz"], rel=1e-6)  # antes 555 083 (3,5·G·J^0,75)


def test_gazetas_dynamics_impedance_has_the_factor_two():
    imp = rectangular_footing_impedance(B_m=2.0, L_m=2.0, G_MPa=76.0, nu=0.35)
    assert imp.vertical.K_static == pytest.approx(EXPECTED["Kz"], rel=1e-6)     # antes 265 415 (×½)
    assert imp.horizontal_x.K_static == pytest.approx(EXPECTED["Ky"], rel=1e-6)
    assert imp.rocking_x.K_static == pytest.approx(EXPECTED["Krx"], rel=1e-6)
    assert imp.rocking_y.K_static == pytest.approx(EXPECTED["Kry"], rel=1e-6)
    assert imp.torsion.K_static == pytest.approx(EXPECTED["Krz"], rel=1e-6)


def test_gazetas_two_modules_agree_on_a_rectangle():
    """Las dos implementaciones del paquete dan lo mismo en 3 × 2 m."""
    G = 50.0  # MPa
    rho = 1900.0
    k = gazetas_stiffness(FootingGeometry(L=3.0, B=2.0), DynSoil(thickness=20.0, Vs=math.sqrt(G * 1e6 / rho), rho=rho, nu=0.3))
    imp = rectangular_footing_impedance(B_m=2.0, L_m=3.0, G_MPa=G, nu=0.3, rho_kg_m3=rho)
    assert k.Kz / 1000 == pytest.approx(imp.vertical.K_static, rel=1e-9)
    assert k.Ky / 1000 == pytest.approx(imp.horizontal_x.K_static, rel=1e-9)
    assert k.Kx / 1000 == pytest.approx(imp.horizontal_y.K_static, rel=1e-9)


# ---------------------------------------------------------------------------
# Punzonamiento: v_min (ec. 6.50)
# ---------------------------------------------------------------------------


def test_punching_resistance_has_v_min_floor():
    """ρ = 0,001, f_ck = 25, d = 0,5 m: k = 1,632.

    C·k·(100ρ·fck)^(1/3) = 0,12·1,6325·2,5^(1/3) = 0,2659 MPa
    v_min = 0,035·1,6325^1,5·√25 = 0,3650 MPa -> gobierna v_min.
    """
    res = punching_shear_check(
        RectangularFoundation(length=3000.0, width=3000.0, thickness=600.0),
        Column(length=400.0, width=400.0, pos_x=1500.0, pos_y=1500.0),
        N_sd_kN=800.0, fck_MPa=25.0, rho_x=0.001, rho_y=0.001, d_eff_m=0.5,
    )
    k = 1 + math.sqrt(200 / 500)
    assert res.tau_rd == pytest.approx(0.035 * k ** 1.5 * 5.0 * 1000.0, rel=1e-9)


# ---------------------------------------------------------------------------
# Pilotes: ξ (EN 1997-1 ec. 7.8)
# ---------------------------------------------------------------------------


def test_pile_correlation_factor_takes_the_governing_quotient():
    """R_c;k = min{R/ξ3 ; R/ξ4} con un solo perfil = R / max(ξ3, ξ4).

    Con ξ3 = 1,35 y ξ4 = 1,27 se dividía por 1,27 (6,3 % alto).
    """
    sand = SoilLayer(name="arena", thickness=20.0, soil_type=SoilType.COHESIONLESS,
                     friction_angle=34.0, unit_weight=19.0)
    prof = SoilProfile(layers=[sand])
    pile = Pile(diameter=600.0, length=12000.0)
    ref = pile_axial_capacity(pile, prof, sand, beta_shaft=0.35, xi3=1.0, xi4=1.0)
    res = pile_axial_capacity(pile, prof, sand, beta_shaft=0.35, xi3=1.35, xi4=1.27)
    assert res.R_ck == pytest.approx(ref.R_ck / 1.35, rel=1e-12)


# ---------------------------------------------------------------------------
# Muro en ménsula
# ---------------------------------------------------------------------------


def test_rankine_inclined_limits():
    # α = 0 -> tan²(45° − φ/2); α = φ -> cos φ (raíz nula).
    assert Ka_rankine_inclined(30.0, 0.0) == pytest.approx(Ka_rankine(30.0), rel=1e-12)
    assert Ka_rankine_inclined(30.0, 30.0) == pytest.approx(math.cos(math.radians(30.0)), rel=1e-12)
    with pytest.raises(ValueError):
        Ka_rankine_inclined(30.0, 35.0)


def _wall(slope=0.0, surcharge=0.0, da=DesignApproach.DA2, passive=False, c_found=0.0):
    from foundationcalc.design.retaining_wall import (
        CantileverWallDesigner, CantileverWallGeometry, RetainingWallLoading,
    )
    geo = CantileverWallGeometry(H=5.0, stem_top=0.30, stem_bottom=0.45, toe=1.0,
                                 heel=2.5, base_thickness=0.55, embedment_front=0.8)
    back = SoilLayer(name="relleno", thickness=10, friction_angle=30.0, unit_weight=19.0)
    found = SoilLayer(name="base", thickness=10, friction_angle=32.0, cohesion=c_found, unit_weight=20.0)
    load = RetainingWallLoading(backfill=back, foundation_soil=found, surcharge_q=surcharge,
                                backfill_slope_deg=slope)
    return CantileverWallDesigner(geo, load, Concrete(fck=30), design_approach=da,
                                  include_passive_in_front=passive)


def test_wall_virtual_back_uses_inclined_rankine():
    """φ = 30°, α = 20°: K_a = 0,4142 (antes 0,3333, el de relleno horizontal).

    P = ½·K_a·γ·H_v², H_v = 5 + 0,55 = 5,55 m, componente horizontal P·cos 20°.
    """
    des = _wall(slope=20.0)
    tp = des._active_thrust_parts()
    Ka = Ka_rankine_inclined(30.0, 20.0)
    assert Ka == pytest.approx(0.41421, abs=1e-4)
    P = 0.5 * Ka * 19.0 * 5.55 ** 2
    assert tp["P_h_earth"] == pytest.approx(P * math.cos(math.radians(20.0)), rel=1e-12)
    assert tp["P_v_earth"] == pytest.approx(P * math.sin(math.radians(20.0)), rel=1e-12)


def test_wall_thrust_uses_design_friction_angle_in_da1_c2():
    """DA1-C2: K_a con φ_d = atan(tan 30°/1,25) = 24,79° y acciones A2 (1,0 G; 1,3 Q).

    Antes el empuje usaba φ_k en todos los enfoques: en DA1-C2 salía un 19 % bajo
    (K_a 0,3333 frente a 0,4091).
    """
    des = _wall(surcharge=10.0, da=DesignApproach.DA1_C2)
    act = des._factored_actions()
    Ka = Ka_rankine(math.degrees(math.atan(math.tan(math.radians(30.0)) / 1.25)))
    H = 5.55
    assert Ka == pytest.approx(0.4091, abs=1e-4)
    assert act.H_d == pytest.approx(1.0 * 0.5 * Ka * 19.0 * H ** 2 + 1.30 * Ka * 10.0 * H, rel=1e-12)


def test_wall_surcharge_thrust_takes_gamma_q():
    """DA1-C1: empuje de tierras ×1,35 y empuje de la sobrecarga ×1,50."""
    des = _wall(surcharge=10.0, da=DesignApproach.DA1_C1)
    act = des._factored_actions()
    Ka = Ka_rankine(30.0)
    H = 5.55
    expected = 1.35 * 0.5 * Ka * 19.0 * H ** 2 + 1.50 * Ka * 10.0 * H
    assert act.H_d == pytest.approx(expected, rel=1e-12)


def test_wall_sliding_divides_the_tangent_and_uses_gamma_re():
    """DA1-C2 (γ_φ = 1,25, γ_R;h = γ_R;e = 1,0) con pasivo delante.

    H_Rd = V_d·tan φ/1,25 + c/1,25·B + P_p/1,0. Antes: tan(φ/1,25) y P_p/1,4.
    """
    des = _wall(da=DesignApproach.DA1_C2, passive=True, c_found=5.0)
    res = des.check()
    pf = get_partial_factors(DesignApproach.DA1_C2, LimitState.GEO)
    assert pf.soil.gamma_phi == 1.25 and pf.resistance.gamma_Re == 1.0
    V = res.actions.V_d
    P_p = passive_thrust(H=0.8, gamma=20.0, phi_deg=32.0, c_prime=5.0).thrust_P
    expected = V * math.tan(math.radians(32.0)) / 1.25 + 5.0 / 1.25 * 3.95 + P_p / 1.0
    assert res.sliding_H_Rd == pytest.approx(expected, rel=1e-12)


def test_wall_heel_and_toe_moments_from_the_real_pressure_diagram():
    """Resultante dentro del núcleo: q(x) = V/B·(1 + 12·e·(B/2 − x)/B²), x desde la puntera.

    Talón (cara en x_h = 1,45 m, longitud 2,5 m) con q de q_a a q_b:
        M = w·l²/2 − l²·(q_a + 2·q_b)/6
    Puntera (longitud 1,0 m) con q de q_0 (borde) a q_t (cara):
        M = l²·(2·q_0 + q_t)/6 − w_t·l²/2
    """
    des = _wall()
    act = des._factored_actions()
    res = des.check()
    B, V, e = 3.95, act.V_d, act.e_x
    assert abs(e) <= B / 6
    q = lambda x: V / B * (1 + 12 * e * (B / 2 - x) / B ** 2)  # noqa: E731
    gG = get_partial_factors(DesignApproach.DA2, LimitState.STR).actions.gamma_G_unfav
    w_heel = gG * (25.0 * 0.55 + 19.0 * 5.0)
    w_toe = gG * (25.0 * 0.55 + 19.0 * 0.8)
    l_h, l_t = 2.5, 1.0
    M_heel = w_heel * l_h ** 2 / 2 - l_h ** 2 * (q(1.45) + 2 * q(B)) / 6
    M_toe = l_t ** 2 * (2 * q(0.0) + q(1.0)) / 6 - w_toe * l_t ** 2 / 2
    assert res.M_heel == pytest.approx(abs(M_heel), rel=1e-4)
    assert res.M_toe == pytest.approx(abs(M_toe), rel=1e-4)
    # Con la resultante hacia la puntera (e > 0) la presión baja hacia el talón.
    assert e > 0 and q(1.45) < q(0.0)


def test_wall_overturning_equ_from_characteristic_values():
    """EQU: M_dst = 1,10·P_h·H/3 + 1,50·P_q·H/2; M_stb = 0,90·Σ W·x (sin sobrecarga).

    Empujes con el φ de cálculo del conjunto EQU (γ_φ = 1,25, EN 1997-1 Tabla A.4):
    φ_d = atan(tan 30°/1,25) = 24,79°.
    """
    des = _wall(surcharge=10.0)
    res = des.check()
    Ka = Ka_rankine(math.degrees(math.atan(math.tan(math.radians(30.0)) / 1.25)))
    H = 5.55
    M_dst = 1.10 * 0.5 * Ka * 19.0 * H ** 2 * H / 3 + 1.50 * Ka * 10.0 * H * H / 2
    W = [
        3.95 * 0.55 * 25.0 * 3.95 / 2,                # base
        0.375 * 5.0 * 25.0 * (1.0 + 0.45 / 2),        # alzado (canto medio)
        2.5 * 5.0 * 19.0 * (1.45 + 1.25),             # relleno sobre el talón
        1.0 * 0.8 * 19.0 * 0.5,                       # tierra sobre la puntera
    ]
    M_stb = 0.90 * sum(W)
    assert res.overturning_utilization == pytest.approx(M_dst / M_stb, rel=1e-12)


# ---------------------------------------------------------------------------
# Zapata combinada trapezoidal
# ---------------------------------------------------------------------------


def test_combined_footing_trapezoid_centroid_on_the_resultant():
    """Columna 1 en el lindero (d = 0, c = 0,40 m), P1 = 600, P2 = 1200 kN, s = 4 m.

    Centro de la columna 1 a c/2 = 0,20 m; x_R = 1200·4/1800 = 2,6667 m;
    resultante a 2,8667 m del lindero. El centroide del trapecio,
    L/3·(B1 + 2·B2)/(B1 + B2), tiene que caer ahí (antes caía en 2,6667).
    """
    from foundationcalc.design.combined_footing import CombinedFootingInputs, design_combined_footing
    r = design_combined_footing(CombinedFootingInputs(
        P1_kN=600.0, P2_kN=1200.0, col_spacing_m=4.0, column_1_to_property_line_m=0.0,
        column_size_m=0.40, q_allow_kPa=200.0))
    assert r.shape == "trapezoidal"
    x_c = r.L_m / 3.0 * (r.B1_m + 2 * r.B2_m) / (r.B1_m + r.B2_m)
    assert x_c == pytest.approx(0.20 + 1200.0 * 4.0 / 1800.0, rel=1e-12)
    assert r.A_provided_m2 == pytest.approx(1800.0 / 200.0, rel=1e-12)
    assert r.x_resultant_m == pytest.approx(1200.0 * 4.0 / 1800.0, rel=1e-12)


# ---------------------------------------------------------------------------
# Memoria de la cadena: el estado global sale de los resultados
# ---------------------------------------------------------------------------


def _package(N, h):
    from foundationcalc._common.model import Reaction
    from foundationcalc.integration.foundation_chain import foundation_package
    return foundation_package(
        etabs_or_reactions=[Reaction(node_id="P1", case="ELU", fz_kN=N)],
        soil_params={"allowable_bearing_kPa": 400.0},
        footing_thickness_m=h,
        column_coordinates={"P1": (0.0, 0.0)},
    )


def test_memoria_says_no_cumple_when_punching_fails():
    pkg = _package(3000.0, 0.30)
    assert pkg.punching_checks["P1"].is_ok is False
    assert "TODAS LAS COMPROBACIONES CUMPLEN" not in pkg.memoria_markdown
    assert "**Estado Global:** NO CUMPLE" in pkg.memoria_markdown
    assert "punzonamiento" in pkg.memoria_markdown.split("**Estado Global:**")[1]


def test_memoria_says_cumple_only_when_everything_passes():
    pkg = _package(600.0, 0.60)
    assert pkg.punching_checks["P1"].is_ok is True
    assert "las comprobaciones incluidas en esta memoria" in pkg.memoria_markdown


# ---------------------------------------------------------------------------
# Servicios, memorias, puentes
# ---------------------------------------------------------------------------


def test_wall_service_bearing_not_evaluated_and_real_lever_arms():
    """H = 4, puntera 0,8, alzado 0,4, talón 1,3, B = 2,5 m, base 0,3 m, q = 0.

    M_res = 38,4·1,0 + 18·1,25 + 93,6·1,85 = 234,06 kN·m/m (antes 150·1,25 = 187,5)
    M_vuelco = ½·(1/3)·18·4²·4/3 = 64 kN·m/m -> FS = 3,657
    """
    from foundationcalc.services.walls import CantileverWallInput, design_cantilever_wall
    r = design_cantilever_wall(CantileverWallInput(
        H=4.0, base_width=2.5, stem_thickness=0.4, toe_width=0.8, heel_width=1.3,
        gamma_soil=18.0, phi_soil=30.0, surcharge_kPa=0.0))
    assert r.bearing_FS is None
    assert r.overturning_FS == pytest.approx(234.06 / 64.0, rel=1e-9)


def test_aci_anchor_steel_shear_phi_is_065():
    """Acero dúctil a cortante: φ = 0,65 (ACI 318-19 Tabla 17.5.3), antes 0,75.

    Vsa = 0,6·157·400 = 37 680 N; borde a 1 m: gobierna el acero.
    """
    r = shear_capacity(Vu=10_000.0, Ase_V=157.0, futa=400.0, fc=30.0, hef=200.0, ca1=1000.0, da=16.0)
    assert r.governing == "steel"
    assert r.phi_Vn == pytest.approx(0.65 * 0.6 * 157.0 * 400.0, rel=1e-12)


def test_liquefaction_silty_sand_threshold_is_20():
    """EN 1998-5 §4.1.4: limo > 35 % y N1(60) > 20 con α·S < 0,15 -> no hace falta."""
    assert liquefaction_screening(5.0, 0.10, silt_fraction=40.0, N_1_60=25.0).required is False
    assert liquefaction_screening(5.0, 0.10, silt_fraction=40.0, N_1_60=18.0).required is True


def test_seismic_thrust_dynamic_increment_counts_water_once():
    """k_v = 0, γ* = 18, K = 0,4, H = 4: estático ½·18·0,4·16 = 57,6 kN/m.

    E_d = 57,6 + 10 + 5 = 72,6; incremento = E_d − 57,6 − E_ws = 5 (antes 30).
    """
    r = seismic_thrust(H=4.0, gamma_star=18.0, K_mo=0.4, kv=0.0, E_ws=10.0, E_wd=5.0)
    assert r.seismic_thrust == pytest.approx(72.6, rel=1e-12)
    assert r.dynamic_increment == pytest.approx(5.0, rel=1e-12)


def test_seismic_footing_block_inertia_arm_is_half_thickness():
    """3 × 3 × 0,7 m, N = 990, H = 180 kN, M = 420 kN·m, a_g = 0,20, S = 1,15.

    k_h = 0,23; W = 9·0,7·25 = 157,5 kN; H_in = 36,225 kN; k_v = 0,115
    N_tot = 990 + 157,5 − 0,115·157,5 = 1129,3875 kN
    M_tot = 420 + 180·0,7 + 36,225·0,35 = 558,67875 kN·m
    e = M_tot/N_tot = 0,49467 m (antes el bloque se contaba con brazo 1,5·t)
    """
    from foundationcalc.analysis.seismic_footing import SeismicAction, seismic_footing_check
    soil = SoilLayer(name="arena", thickness=10, friction_angle=34.0, unit_weight=19.0)
    r = seismic_footing_check(
        RectangularFoundation(length=3000.0, width=3000.0, thickness=700.0, embedment_depth=1200.0),
        Column(length=500.0, width=500.0, pos_x=1500.0, pos_y=1500.0),
        N_kN=990.0, H_kN=180.0, M_kNm=420.0, soil=soil, concrete=Concrete(fck=30),
        seismic=SeismicAction(a_g=0.20, S=1.15),
    )
    assert r.M_d == pytest.approx(558.67875, rel=1e-12)
    assert r.N_d == pytest.approx(1129.3875, rel=1e-12)
    assert r.e_y == pytest.approx(558.67875 / 1129.3875, abs=1e-4)


def test_fastsap_bridge_does_not_invent_reactions():
    from foundationcalc.exceptions import FastSAPBridgeError
    from foundationcalc.integration.fastsap_bridge import FastSAPFoundationPipeline
    with pytest.raises(FastSAPBridgeError):
        FastSAPFoundationPipeline().extract_reactions(["1"])


def test_single_version_everywhere():
    import foundationcalc
    root = Path(__file__).resolve().parents[1]
    pyproj = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproj["project"]["version"] == foundationcalc.__version__ == "1.1.0"
    pytest.importorskip("fastapi")
    from foundationcalc.api.app import app
    assert app.version == foundationcalc.__version__


# ---------------------------------------------------------------------------
# Pilote con carga lateral: condiciones de contorno en cabeza
# ---------------------------------------------------------------------------


def _bvp_linear_pile(H, M, fixed, EI=200000.0, k=20000.0, L=20.0):
    """Oráculo independiente: EI·y'''' + k·z·y = 0 resuelto con scipy.solve_bvp.

    Cabeza libre: EI·y''(0) = M, EI·y'''(0) = H; encepada: y'(0) = 0, EI·y'''(0) = H.
    Punta libre: y'' = y''' = 0.
    """
    from scipy.integrate import solve_bvp

    def f(z, Y):
        return np.vstack([Y[1], Y[2], Y[3], -k * z * Y[0] / EI])

    def bc(a, b):
        head = [a[1], EI * a[3] - H] if fixed else [EI * a[2] - M, EI * a[3] - H]
        return np.array(head + [b[2], b[3]])

    z = np.linspace(0.0, L, 201)
    sol = solve_bvp(f, bc, z, np.zeros((4, z.size)), tol=1e-8, max_nodes=20000)
    Y = sol.sol(np.array([0.0]))
    return float(Y[0][0]), float(EI * Y[2][0])


@pytest.mark.parametrize("H,M,fixed", [(0.01, 0.0, False), (0.0, 0.01, False), (0.01, 0.0, True)])
def test_pile_lateral_head_conditions_match_linear_bvp(H, M, fixed):
    """Reese con cargas diminutas = suelo lineal k·z (k = 20 MN/m³), EI = 200 MN·m².

    Antes de la 1.1.0: con momento en cabeza el término M·h²/EI de la fila 1 se
    perdía (2,5 mm con 80 tramos y 7,9 mm con 200 para 10 kN·m), y la cabeza
    encepada ignoraba H (desplazamiento nulo). Ahora coinciden con solve_bvp y
    con los coeficientes de Matlock y Reese (y = 2,435·H·T³/EI,
    1,623·M·T²/EI; encepado 0,93·H·T³/EI y M = −0,93·H·T).
    """
    from foundationcalc.analysis.pile_lateral import PileLateral, PYSoilLayer, PYType, solve_pile_lateral
    pile = PileLateral(
        length_m=20.0, diameter_m=0.6, EI_kNm2=200000.0,
        layers=[PYSoilLayer(z_top_m=0.0, z_bot_m=20.0, py_type=PYType.REESE_SAND,
                            phi_deg=35.0, gamma_eff_kN_m3=10.0, k_pa_per_m=20000.0)],
        head_load_H_kN=H, head_moment_M_kNm=M, fixed_head=fixed)
    r = solve_pile_lateral(pile, n_segments=200, max_iter=300, tol_mm=1e-6)
    y0, M0 = _bvp_linear_pile(H, M, fixed)
    assert r.y_m[0] == pytest.approx(y0, rel=1e-2)
    assert r.M_kNm[0] == pytest.approx(M0, rel=1e-2, abs=1e-9)
    T = (200000.0 / 20000.0) ** 0.2
    if fixed:
        assert r.M_kNm[0] == pytest.approx(-0.93 * H * T, rel=1e-2)


# ---------------------------------------------------------------------------
# CPT: tensión vertical y perfil derivado
# ---------------------------------------------------------------------------


def _cpt(step=0.2, n=75):
    from foundationcalc.analysis.cpt import CPTProfile, CPTReading
    rows = [CPTReading(depth=round(step * (i + 1), 3), q_c_MPa=5.0, f_s_kPa=30.0) for i in range(n)]
    return CPTProfile(readings=rows, water_table_depth_m=2.0, gamma_above_wt_kN_m3=18.0, gamma_below_wt_kN_m3=19.0)


@pytest.mark.parametrize("z,expected", [(1.0, 18.0), (2.0, 36.0), (4.0, 74.0), (4.1, 75.9), (12.0, 226.0)])
def test_cpt_total_stress_closed_form(z, expected):
    """σ_v0 = 18·min(z, 2) + 19·max(z − 2, 0). Antes, a 4,0 m: 73,8 kPa (último tramo con γ seco)."""
    assert _cpt().total_stress_kPa(z) == pytest.approx(expected, rel=1e-12)


def test_cpt_derived_profile_starts_at_the_surface():
    """Con lecturas desde 0,2 m y 4 bandas, el primer estrato llega a la superficie y los contactos
    caen en los bordes de banda (antes subían 0,2 m)."""
    from foundationcalc.analysis.cpt import CPTProfile, CPTReading
    from foundationcalc.analysis.cpt_to_design import soil_profile_from_cpt
    rows = []
    for i in range(1, 76):
        z = round(0.2 * i, 2)
        qc, fs, u2 = (12.0, 70.0, 0.0) if z <= 3.9 else ((0.9, 18.0, 60.0 + 9.81 * (z - 2.0)) if z <= 7.6 else (18.0, 110.0, 9.81 * (z - 2.0)))
        rows.append(CPTReading(depth=z, q_c_MPa=qc, f_s_kPa=fs, u_2_kPa=u2))
    cpt = CPTProfile(readings=rows, water_table_depth_m=2.0)
    prof = soil_profile_from_cpt(cpt, n_layers=4)
    tops = np.cumsum([0.0] + [layer.thickness for layer in prof.layers])
    assert tops[1] == pytest.approx(3.9, abs=1e-9)
    assert tops[2] == pytest.approx(7.6, abs=1e-9)
    assert prof.total_depth == pytest.approx(15.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Zapata combinada: diagrama de flectores
# ---------------------------------------------------------------------------


def test_combined_footing_moments_signs_and_reinforcement():
    """P1 = 900, P2 = 1300 kN, s = 5 m, d = 0,5 m, c = 0,45 m, q = 200 kPa (rectangular).

    L = 2·(0,725 + 2,9545) = 7,3591 m; w = 2200/L = 298,95 kN/m.
    Entre pilares el cortante se anula en x0 = P1/w = 3,0106 m:
        M = w·x0²/2 − P1·(x0 − 0,725) = −702,2 kN·m (tracción arriba).
    Bajo el pilar 2: M = w·5,725²/2 − 900·5,0 = +399,1 kN·m (tracción abajo).
    Antes: el −702 no aparecía y la armadura superior salía de los +399.
    """
    from foundationcalc.core.material import ReinforcingSteel
    from foundationcalc.design.combined_footing import CombinedFootingInputs, design_combined_footing
    from foundationcalc.design.reinforcement import flexural_reinforcement
    r = design_combined_footing(CombinedFootingInputs(
        P1_kN=900.0, P2_kN=1300.0, col_spacing_m=5.0, column_1_to_property_line_m=0.5,
        column_size_m=0.45, q_allow_kPa=200.0))
    L = 2 * (0.725 + 1300 * 5 / 2200)
    w = 2200 / L
    x0 = 900 / w
    M_neg = w * x0 ** 2 / 2 - 900 * (x0 - 0.725)
    M_pos = w * 5.725 ** 2 / 2 - 900 * 5.0
    assert r.M_neg_kNm == pytest.approx(M_neg, rel=1e-9)
    assert r.M_pos_kNm == pytest.approx(M_pos, rel=1e-4)
    d = 600 - 80
    top = flexural_reinforcement(abs(M_neg), r.B_m * 1000, d, Concrete(fck=30), ReinforcingSteel(fyk=500))
    assert r.As_top_mm2 == pytest.approx(top.As_provided, rel=1e-9)
    assert r.As_top_mm2 > r.As_bot_mm2


# ---------------------------------------------------------------------------
# Losa sobre Winkler: elemento de Mindlin sin modo espurio (MITC4)
# ---------------------------------------------------------------------------


def test_mat_plate_matches_hetenyi_infinite_plate_on_winkler():
    """Placa infinita sobre Winkler bajo carga puntual (Hetényi):
        w(r) = −P/(2·π·k·l²)·kei(r/l),  l = (D/k)^(1/4),  D = E·h³/(12·(1 − ν²)).
    Losa de 24 × 24 m (> 4·l a cada lado), h = 0,7 m, k = 20 MN/m³, P = 1000 kN,
    elementos de 0,75 m. Antes, con la cortante integrada en un punto, el modo en
    damero dejaba w un 9-13 % por debajo a una longitud característica.
    """
    from scipy.special import kei
    from foundationcalc import MatFoundationSolver
    E, nu, k, P, h = 30e6, 0.2, 20000.0, 1000.0, 0.7
    D = E * h ** 3 / (12 * (1 - nu ** 2))
    l = (D / k) ** 0.25
    s = MatFoundationSolver(length=24.0, width=24.0, thickness=h, nx=32, ny=32, E_concrete=E, nu_concrete=nu, k_s=k)
    s.add_column_load(12.0, 12.0, P)
    r = s.solve(allow_uplift=False)
    for rr in (1.5, 3.0, 4.5):
        w_an = -P / (2 * math.pi * k * l ** 2) * kei(rr / l)
        assert r.w[s.node_at(12.0 + rr, 12.0)] == pytest.approx(w_an, rel=0.03)


def test_mat_plate_has_no_checkerboard_under_a_column():
    """Losa gruesa (h = 3 m) con un pilar: el asiento decrece con la distancia a lo largo del eje.

    Antes alternaba entre nudos vecinos (0,86 / 0,01 / 0,86 mm).
    """
    from foundationcalc import MatFoundationSolver
    s = MatFoundationSolver(length=12.0, width=10.0, thickness=3.0, nx=24, ny=20, E_concrete=30e6, k_s=20000.0)
    s.add_column_load(6.0, 5.0, 1000.0)
    r = s.solve(allow_uplift=False)
    row = [r.w[s.node_at(6.0 + 0.5 * i, 5.0)] for i in range(0, 12)]
    assert all(a >= b for a, b in zip(row, row[1:]))
    assert min(row) > 0


# ---------------------------------------------------------------------------
# Muros de gravedad, contrafuertes, tierra armada, pantallas y flotación
# ---------------------------------------------------------------------------


def _phi_d(phi_k: float, gamma_phi: float) -> float:
    return math.degrees(math.atan(math.tan(math.radians(phi_k)) / gamma_phi))


def test_gravity_wall_thrust_uses_design_phi_and_gamma_q_on_surcharge():
    """Muro de gravedad de hormigón en masa, H = 4 m, φ' = 32°, q = 10 kPa.

    DA1-C2 (M2, γ_φ = 1,25): K_a de Coulomb con φ_d = 26,56° y δ_w = ⅔·φ_d.
    Antes usaba φ_k (K_a = 0,2814 frente a 0,3517, empuje un 20 % bajo).
    DA1-C1: la sobrecarga se mayora con γ_Q = 1,5, no con γ_G = 1,35.
    """
    from foundationcalc.analysis.earth_pressure import Ka_coulomb
    from foundationcalc.design.gravity_wall import GravityWallDesigner, GravityWallGeometry, GravityWallLoading
    bf = SoilLayer(name="relleno", thickness=10, soil_type=SoilType.COHESIONLESS, friction_angle=32.0, unit_weight=19.0)
    fd = SoilLayer(name="apoyo", thickness=10, soil_type=SoilType.COHESIONLESS, friction_angle=32.0, unit_weight=20.0)
    geo = GravityWallGeometry(H=4.0, top_width=0.6, stem_bottom=2.2)
    load = GravityWallLoading(backfill=bf, foundation_soil=fd, surcharge_q=10.0)
    r2 = GravityWallDesigner(geo, load, design_approach=DesignApproach.DA1_C2).check()
    pd = _phi_d(32.0, 1.25)
    assert r2.K_a == pytest.approx(Ka_coulomb(pd, 2.0 / 3.0 * pd, 90.0, 0.0), rel=1e-12)
    assert r2.K_a > Ka_coulomb(32.0, 2.0 / 3.0 * 32.0, 90.0, 0.0) * 1.2
    r1 = GravityWallDesigner(geo, load, design_approach=DesignApproach.DA1_C1).check()
    K = Ka_coulomb(32.0, 2.0 / 3.0 * 32.0, 90.0, 0.0)
    c = math.cos(math.radians(2.0 / 3.0 * 32.0))
    H_d = 1.35 * 0.5 * K * 19.0 * 16.0 * c + 1.5 * K * 10.0 * 4.0 * c
    assert r1.H_d == pytest.approx(H_d, rel=1e-12)


def test_mse_external_thrust_uses_design_phi():
    """Bloque de tierra armada H = 6 m, B = 4,2 m, φ_relleno = 34°, DA1-C2: K_a con φ_d."""
    from foundationcalc.design.mse_wall import (
        MSELayer, MSELoading, MSEReinforcementType, MSEWallDesigner, MSEWallGeometry,
    )
    layers = [MSELayer(z_below_top_m=z, length_m=4.2, reinforcement_type=MSEReinforcementType.STEEL_STRIP,
                       spacing_vertical_m=0.75) for z in (0.375, 1.125, 1.875)]
    geo = MSEWallGeometry(H=6.0, B_reinforced=4.2, layers=layers)
    load = MSELoading(phi_fill_deg=34.0, gamma_fill_kN_m3=19.0, surcharge_q=10.0,
                      phi_foundation_deg=30.0, gamma_foundation_kN_m3=19.0)
    r = MSEWallDesigner(geo, load, design_approach=DesignApproach.DA1_C2).check()
    Ka = Ka_rankine(_phi_d(34.0, 1.25))
    assert r.external.P_a_h_kN_per_m == pytest.approx(0.5 * Ka * 19.0 * 36.0 + Ka * 10.0 * 6.0, rel=1e-12)


def test_counterfort_stem_pressure_uses_design_phi_of_str_set():
    """Muro de contrafuertes H = 8 m, φ' = 30°, q = 10 kPa, contrafuertes a 3 m, DA1-C2.

    Presión en la base del alzado p = γ_G·K_a,d·γ·H + γ_Q·K_a,d·q (Coulomb con φ_d) y momentos de losa
    continua p·L²/12 y p·L²/24.
    """
    from foundationcalc.design.counterfort_wall import CounterfortWallDesigner, CounterfortWallGeometry
    from foundationcalc.design.retaining_wall import RetainingWallLoading
    bf = SoilLayer(name="relleno", thickness=10, soil_type=SoilType.COHESIONLESS, friction_angle=30.0, unit_weight=19.0)
    fd = SoilLayer(name="apoyo", thickness=10, soil_type=SoilType.COHESIONLESS, friction_angle=33.0, unit_weight=20.0)
    geo = CounterfortWallGeometry(H=8.0, stem_thickness=0.35, toe=1.2, heel=4.0, base_thickness=0.7,
                                  counterfort_spacing_m=3.0, counterfort_thickness_m=0.4)
    load = RetainingWallLoading(backfill=bf, foundation_soil=fd, surcharge_q=10.0)
    r = CounterfortWallDesigner(geo, load, Concrete(fck=30), design_approach=DesignApproach.DA1_C2).check()
    from foundationcalc.analysis.earth_pressure import Ka_coulomb
    pf = get_partial_factors(DesignApproach.DA1_C2, LimitState.STR)
    pd = _phi_d(30.0, pf.soil.gamma_phi)
    Ka = Ka_coulomb(pd, 2.0 / 3.0 * pd, 90.0, 0.0)   # RetainingWallLoading: Coulomb, δ = ⅔φ por defecto
    p = pf.actions.gamma_G_unfav * Ka * 19.0 * 8.0 + pf.actions.gamma_Q_unfav * Ka * 10.0
    assert r.stem_M_support_kNm_per_m == pytest.approx(p * 9.0 / 12.0, rel=1e-12)
    assert r.stem_M_midspan_kNm_per_m == pytest.approx(p * 9.0 / 24.0, rel=1e-12)


def test_diaphragm_wall_prop_force_and_moment_from_equilibrium():
    """Pantalla H = 10 m, ficha 7 m, puntal en cabeza, φ' = 32°, γ = 20, DA2.

    Soporte libre: P_p,mob = M_a/brazo_p, T = P_a − P_p,mob = 272,4 kN/m; el cortante se
    anula a z0 = √(2T/k) = 8,10 m (k = γ_G·K_a·γ) y M_max = ⅔·T·z0 = 1472 kN·m/m.
    Antes: T = P_a − P_p = 59,7 kN/m y M_max = T²/(2·q_max) = 12,6 kN·m/m.
    """
    from foundationcalc.design.diaphragm_wall import (
        DiaphragmWallDesigner, DiaphragmWallGeometry, DiaphragmWallLoading,
    )
    geo = DiaphragmWallGeometry(H_excavation=10.0, embedment_m=7.0, thickness_m=0.8, prop_levels_m=[0.0])
    r = DiaphragmWallDesigner(geo, DiaphragmWallLoading(phi_deg=32.0, gamma_kN_m3=20.0)).check()
    Ka, Kp = Ka_rankine(32.0), math.tan(math.radians(61.0)) ** 2
    k = 1.35 * Ka * 20.0
    Pa = k * 17.0 ** 2 / 2.0
    Ma = Pa * 2.0 / 3.0 * 17.0
    arm_p = 10.0 + 14.0 / 3.0
    Pp = 0.5 * Kp * 20.0 * 49.0 / 1.4
    T = Pa - Ma / arm_p
    z0 = math.sqrt(2.0 * T / k)
    assert r.P_passive_kN_per_m == pytest.approx(Pp, rel=1e-12)
    assert r.overturning_safety_factor == pytest.approx(Pp * arm_p / Ma, rel=1e-12)
    assert r.prop_forces_kN_per_m[0] == pytest.approx(T, rel=1e-12)
    assert r.M_max_kNm_per_m == pytest.approx(2.0 / 3.0 * T * z0, rel=1e-4)
    assert r.z_of_M_max_m == pytest.approx(z0, abs=0.01)


def test_diaphragm_wall_refuses_cohesion_and_water_it_does_not_model():
    from foundationcalc.design.diaphragm_wall import (
        DiaphragmWallDesigner, DiaphragmWallGeometry, DiaphragmWallLoading,
    )
    geo = DiaphragmWallGeometry(H_excavation=10.0, embedment_m=7.0, prop_levels_m=[0.0])
    for kw in ({"c_kPa": 5.0}, {"water_table_above_excavation_m": 2.0}):
        with pytest.raises(ValueError):
            DiaphragmWallDesigner(geo, DiaphragmWallLoading(phi_deg=32.0, gamma_kN_m3=20.0, **kw)).check()


def test_buoyancy_eu_requires_at_least_one_over_0_9():
    """UPL (EN 1997-1): γ_G;dst·U ≤ 0,9·W con γ_G;dst ≥ 1,0 → W/U ≥ 1,111. Antes bastaba 1,10."""
    from foundationcalc.design.buoyancy_check import BuoyancyInput, check_buoyancy
    U = 9.81 * 3.0 * 100.0
    r = check_buoyancy(BuoyancyInput(base_area_m2=100.0, submerged_depth_m=3.0,
                                     structure_weight_kN=1.105 * U, code="EU"))
    assert r.required_FS == pytest.approx(1.0 / 0.9)
    assert not r.passes
