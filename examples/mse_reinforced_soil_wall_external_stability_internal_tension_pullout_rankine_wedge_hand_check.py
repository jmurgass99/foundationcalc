"""Muro de tierra armada: estabilidad externa como bloque rígido e interna capa a capa (tracción y arrancamiento tras la cuña de Rankine).

Muro de 6,0 m con bloque armado de 4,2 m (0,7·H), relleno granular φ' = 34°,
γ = 19 kN/m³, sobrecarga 10 kPa, apoyo φ' = 30°. Armaduras cada 0,75 m.
`MSEWallDesigner` hace:
- externa: peso del bloque B·H·γ, empuje de Rankine del terreno trasero con
  φ_d (M2 en DA1-C2 y DA3; corregido en la 1.1.0, antes φ_k) y sobrecarga con
  γ_Q, deslizamiento con δ = min(⅔·φ_apoyo,d; φ_relleno,d), portante con el
  término de N_γ sobre B' = B − 2e;
- interna: T_max = K_a·(γ·z + q)·S_v, longitud activa
  L_a = (H − z)/tan(45° + φ/2) y arrancamiento 2·L_e·F*·σ_v.
Se compara con dos tipos de armadura (tira de acero y geomalla PET) y se
recalcula a mano una capa. Las resistencias de armadura (_T_ALLOW) y F* son
valores ilustrativos del módulo, no de un fabricante.

Ejecutar:  python examples/mse_reinforced_soil_wall_external_stability_internal_tension_pullout_rankine_wedge_hand_check.py
"""
import math

from foundationcalc.codes.eurocode7 import DesignApproach
from foundationcalc.design.mse_wall import MSELayer, MSELoading, MSEReinforcementType, MSEWallDesigner, MSEWallGeometry


def geometry(kind: MSEReinforcementType, L: float) -> MSEWallGeometry:
    zs = [0.375 + 0.75 * i for i in range(8)]
    return MSEWallGeometry(H=6.0, B_reinforced=L, layers=[
        MSELayer(z_below_top_m=z, length_m=L, reinforcement_type=kind, spacing_vertical_m=0.75) for z in zs])


def main() -> None:
    load = MSELoading(phi_fill_deg=34.0, gamma_fill_kN_m3=19.0, surcharge_q=10.0,
                      phi_foundation_deg=30.0, gamma_foundation_kN_m3=19.0)
    print("Estabilidad externa, bloque de 6,0 × 4,2 m:")
    print(f"  {'enfoque':<7} {'W [kN/m]':>8} {'P_h [kN/m]':>10} {'e [m]':>6} {'desliz.':>7} {'vuelco':>6} {'portante':>8} {'q_max':>6}")
    for da in (DesignApproach.DA1_C1, DesignApproach.DA1_C2, DesignApproach.DA2, DesignApproach.DA3):
        ex = MSEWallDesigner(geometry(MSEReinforcementType.STEEL_STRIP, 4.2), load, design_approach=da).check().external
        print(f"  {da.value:<7} {ex.W_kN_per_m:8.1f} {ex.P_a_h_kN_per_m:10.1f} {ex.e_x_m:6.3f} {ex.sliding_utilization:7.3f} "
              f"{ex.overturning_utilization:6.3f} {ex.bearing_utilization:8.3f} {ex.q_max_kPa:6.1f}"
              + ("" if ex.all_ok else "  <- no cumple"))
    Ka = math.tan(math.radians(45 - 17)) ** 2
    print(f"  A mano (DA2): K_a = tan²(45° − 17°) = {Ka:.4f}; W = 4,2·6·19 = {4.2 * 6 * 19:.1f}; "
          f"P_h = ½·K_a·19·6² + K_a·10·6 = {0.5 * Ka * 19 * 36 + Ka * 60:.1f} kN/m")

    print("\nEstabilidad interna (DA2), por capa:")
    for kind in (MSEReinforcementType.STEEL_STRIP, MSEReinforcementType.GEOGRID_PET):
        res = MSEWallDesigner(geometry(kind, 4.2), load).check()
        print(f"  {kind.value}:")
        print(f"    {'z [m]':>5} {'T_max':>6} {'T_adm':>6} {'tracción':>8} {'L_a':>5} {'L necesaria':>11} {'arrancam.':>9}")
        for c in res.internal:
            print(f"    {c.z_m:5.3f} {c.T_max_kN_per_m:6.2f} {c.T_design_kN_per_m:6.1f} {c.tensile_utilization:8.3f} "
                  f"{(6.0 - c.z_m) / math.tan(math.radians(45.0 + 34.0 / 2)):5.2f} "
                  f"{c.pullout_length_required_m:11.2f} {c.pullout_utilization:9.3f}" + ("" if c.ok else "  <- no cumple"))
        bad = [c.z_m for c in res.internal if not c.ok]
        print(f"    -> {'todas las capas cumplen' if not bad else 'fallan las capas a z = ' + ', '.join(f'{z:.3f}' for z in bad) + ' m'}")

    z = 0.375
    sv = 19 * z + 10
    T = Ka * sv * 0.75
    La = (6 - z) / math.tan(math.radians(62))
    Le = 4.2 - La
    print(f"\nA mano, capa superior de tira (z = {z} m): σ_v = 19·{z} + 10 = {sv:.3f} kPa, T = K_a·σ_v·S_v = {T:.3f} kN/m; "
          f"L_a = (6 − {z})/tan 62° = {La:.3f} m, L_e = 4,2 − L_a = {Le:.3f} m; "
          f"arrancamiento 2·L_e·0,40·σ_v = {2 * Le * 0.40 * sv:.2f} kN/m -> utilización {T / (2 * Le * 0.40 * sv):.3f}")
    print("Límites: K_r = K_a en todas las capas y superficie de Rankine desde el pie para cualquier armadura (AASHTO "
          "distingue armaduras inextensibles con K_r/K_a > 1 y superficie bilineal, sin contrastar aquí); arrancamiento "
          "sin factor de escala ni coeficientes parciales; la utilización de arrancamiento de la capa superior es "
          "grande porque σ_v es pequeña cerca de coronación.")


if __name__ == "__main__":
    main()
