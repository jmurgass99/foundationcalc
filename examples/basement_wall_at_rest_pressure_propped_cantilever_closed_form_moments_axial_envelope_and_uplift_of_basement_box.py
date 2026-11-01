"""Muro de sótano con empuje al reposo: reacciones y momentos frente a las fórmulas cerradas, envolvente con axil excéntrico y flotación del vaso.

Muro de 3,5 m entre la losa de cimentación y el forjado de planta baja,
espesor 0,30 m; relleno φ' = 30°, γ = 19 kN/m³, sobrecarga 10 kPa; axil de
servicio N_max = 150 kN/m con excentricidad 5 cm en cabeza.
`BasementWallDesigner` toma K_0 = (1 − sen φ)·OCR^(sen φ) (Jaky; Mayne y
Kulhawy) y una presión trapecial q(z) = K_0·(γ·z + q) que descompone en un
rectángulo w = K_0·q y un triángulo Δ = K_0·γ·H. Fórmulas de viga (Roark;
cualquier prontuario):
- ménsula: R_base = w·H + Δ·H/2, M_base = −(w·H²/2 + Δ·H²/6);
- empotrado-apoyado (apoyo en cabeza): R_cabeza = 3wH/8 + ΔH/10,
  M_base = −(wH²/8 + ΔH²/15);
- biapoyado: R_cabeza = wH/2 + ΔH/6, R_base = wH/2 + ΔH/3.
Los máximos de vano se comparan con la derivada nula de M(z) en una malla
fina (el módulo usa 21 puntos). Después, la envolvente de tres combinaciones
(presión + N_min, presión + N_max, sólo N_max), la comprobación global con
factores de seguridad (Rankine y Coulomb) y la flotación del vaso de sótano
con `check_buoyancy` (UPL de EN 1997-1: W/U ≥ 1/0,9, corregido en la 1.1.0).

Ejecutar:  python examples/basement_wall_at_rest_pressure_propped_cantilever_closed_form_moments_axial_envelope_and_uplift_of_basement_box.py
"""
import math

import numpy as np

from foundationcalc.design.basement_wall import (
    BasementWallDesigner, BasementWallGeometry, BasementWallLoading, PressureDiagram, SupportConfig,
    evaluate_wall_stability_coulomb_rankine,
)
from foundationcalc.design.buoyancy_check import BuoyancyInput, check_buoyancy, required_ballast_kN


def main() -> None:
    H, phi, g, q = 3.5, 30.0, 19.0, 10.0
    geo = BasementWallGeometry(height=H, thickness=0.30, eccentricity_top=0.05)
    load = BasementWallLoading(phi_deg=phi, gamma_soil=g, surcharge_q=q, N_min_kN_per_m=0.0, N_max_kN_per_m=150.0)
    K0 = 1 - math.sin(math.radians(phi))
    w, D = K0 * q, K0 * g * H
    print(f"K_0 = 1 − sen 30° = {K0:.3f} (paquete {load.K0:.3f}); q(0) = {w:.2f} kPa, q(H) = {w + D:.2f} kPa")

    hand = {
        SupportConfig.CANTILEVER: (0.0, w * H + D * H / 2, -(w * H ** 2 / 2 + D * H ** 2 / 6)),
        SupportConfig.PROPPED_CANTILEVER: (3 * w * H / 8 + D * H / 10, None, -(w * H ** 2 / 8 + D * H ** 2 / 15)),
        SupportConfig.PINNED_PINNED: (w * H / 2 + D * H / 6, w * H / 2 + D * H / 3, 0.0),
    }
    print(f"\n{'apoyos':<20} {'R_cab':>6} {'a mano':>6} {'R_base':>6} {'a mano':>6} {'M_base':>7} {'a mano':>7} "
          f"{'M_vano(21 p)':>12} {'M_vano exacto':>13} {'z [m]':>5}")
    # Presión sola (sin axil) para comparar con las fórmulas de viga
    geo0 = BasementWallGeometry(height=H, thickness=0.30)
    load0 = BasementWallLoading(phi_deg=phi, gamma_soil=g, surcharge_q=q, N_max_kN_per_m=0.0)
    for sup, (Rt, Rb, Mb) in hand.items():
        r = BasementWallDesigner(geo0, load0, support=sup).solve()
        Rb = Rb if Rb is not None else w * H + D * H / 2 - Rt
        z = np.linspace(0, H, 35001)
        M = Rt * z - w * z ** 2 / 2 - D * z ** 3 / (6 * H)
        M_base = r.M_envelope_outer[-1]
        if M.max() > 1e-9:
            span = f"{r.M_inner_max_kNm:12.2f} {M.max():13.2f} {z[M.argmax()]:5.2f}"
        else:
            span = f"{'—':>12} {'—':>13} {'—':>5}"
        print(f"{sup.value:<20} {r.R_top_kN_per_m:6.2f} {Rt:6.2f} {r.R_base_kN_per_m:6.2f} {Rb:6.2f} "
              f"{M_base:7.2f} {Mb:7.2f} {span}")
    print("  (M > 0 tracciona la cara interior, M < 0 la cara del terreno; momentos en kN·m/m)")

    print("\nEnvolvente empotrado-apoyado con axil (e_1 = 5 cm en cabeza):")
    for pdiag in (PressureDiagram.TRIANGULAR, PressureDiagram.RECTANGULAR):
        r = BasementWallDesigner(geo, load, support=SupportConfig.PROPPED_CANTILEVER, pressure=pdiag).solve()
        print(f"  {pdiag.value:<11}: q = {r.q_top_kPa:5.2f}…{r.q_base_kPa:5.2f} kPa, cara terreno M = {r.M_outer_max_kNm:6.2f} "
              f"a z = {r.z_of_M_outer_max_m:.3f} m, cara interior M = {r.M_inner_max_kNm:6.2f} a z = {r.z_of_M_inner_max_m:.3f} m, "
              f"V_max = {r.V_max_kN:5.2f} kN/m")
    r = BasementWallDesigner(geo, load, support=SupportConfig.PROPPED_CANTILEVER).solve()
    print(f"  En cabeza N_max·e_1 = 150·0,05 = {150 * 0.05:.2f} kN·m/m tracciona la cara interior "
          f"(envolvente en z = 0: {r.M_envelope_inner[0]:.2f}).")
    print("  El diagrama rectangular (0,67·K_0·(γH + q)) es una regla de apuntes del módulo: con él la resultante "
          f"es {0.67 * K0 * (g * H + q) * H / ((w + w + D) / 2 * H):.2f} veces la trapecial.")

    print("\nComprobación global como muro libre (factores de seguridad, FS ≥ 1,5 del módulo):")
    for method in ("rankine", "coulomb"):
        s = evaluate_wall_stability_coulomb_rankine(H, 0.30, g, phi, surcharge_q_kPa=q, N_axial_kN_per_m=150.0,
                                                    base_width_m=1.6, delta_deg=20.0, method=method)
        print(f"  {method:<8}: K_a = {s.Ka:.4f}, P = {s.total_active_thrust_kN_per_m:6.1f} kN/m, "
              f"FS desliz. = {s.FS_sliding:.2f} ({'≥' if s.is_safe_sliding else '<'} 1,5), "
              f"FS vuelco = {s.FS_overturning:.2f} ({'≥' if s.is_safe_overturning else '<'} 1,5)")
    Ka = math.tan(math.radians(45 - phi / 2)) ** 2
    P = 0.5 * Ka * g * H ** 2 + Ka * q * H
    W = 25 * 0.30 * H
    print(f"  A mano (Rankine): P = ½·{Ka:.4f}·19·3,5² + {Ka:.4f}·10·3,5 = {P:.1f}; FS desliz. = (W + N)·0,5/P = "
          f"({W:.2f} + 150)·0,5/{P:.1f} = {(W + 150) * 0.5 / P:.2f}")

    print("\nFlotación del vaso de sótano 20 × 15 m con el freático a 3,0 m sobre la cara inferior de la losa:")
    U = 9.81 * 3.0 * 300.0
    for W_struct in (9000.0, 9600.0, 10500.0, 13500.0):
        cells = []
        for code in ("EU", "USA"):
            b = check_buoyancy(BuoyancyInput(base_area_m2=300.0, submerged_depth_m=3.0, structure_weight_kN=W_struct, code=code))
            ballast = required_ballast_kN(BuoyancyInput(base_area_m2=300.0, submerged_depth_m=3.0, structure_weight_kN=W_struct, code=code))
            cells.append(f"{code} (≥ {b.required_FS:.3f}): {'cumple' if b.passes else f'falta lastre {ballast:.0f} kN'}")
        print(f"  W = {W_struct:6.0f} kN, U = 9,81·3·300 = {U:.0f} kN, W/U = {W_struct / U:.3f} -> " + "; ".join(cells))
    print("  Antes de la 1.1.0 el criterio europeo era W/U ≥ 1,10, por debajo de 1/0,9 = 1,111 (γ_G;stb = 0,9).")
    print("Límites: con agua el módulo suma γ_w·H_w a la ordenada de la base y la reparte linealmente en toda la "
          "altura además de usar γ total (del lado seguro); el diagrama sin axil sale con 21 puntos y el máximo de "
          "vano se queda corto; la comprobación global es de factores de seguridad, no EN 1997-1.")


if __name__ == "__main__":
    main()
