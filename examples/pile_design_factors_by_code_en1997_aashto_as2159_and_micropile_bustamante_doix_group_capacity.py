"""Factores de capacidad de pilotes según el código (EN 1997-1, AASHTO LRFD, AS 2159) y micropilotes tipo Bustamante-Doix en grupo.

1) `design_pile_capacity` convierte una capacidad última de fuste y punta en
   capacidad de cálculo con los factores que trae el módulo para cada código
   (EU: γ = 1,10 hincado / 1,40 perforado; US/CO: φ_s y φ_p; AU: φ_g según el
   riesgo geotécnico). Se recalcula a mano.
2) Micropilote inyectado (IRS) en arena con grava: perforación Ø150 mm,
   diámetro eficaz max(d_s, α·d_d) con α = 1,2, bulbo de 8 m, q_s del extremo
   inferior de la tabla de Bustamante-Doix del módulo (80 kPa), ξ = 1,3 y
   γ_t = 1,5: R_d = π·d·L·q_s/(ξ·γ_t). Después un grupo de 6 bajo una zapata
   existente con N_d = 1400 kN.

Ejecutar:  python examples/pile_design_factors_by_code_en1997_aashto_as2159_and_micropile_bustamante_doix_group_capacity.py
"""
import math

from foundationcalc.design.strengthening import (
    MicropileGeometry, MicropileSoilType, micropile_capacity, micropile_group_capacity,
)
from foundationcalc.pile_capacity_multi import PileCapacityInput, design_pile_capacity


def main() -> None:
    Qs, Qp = 2000.0, 1500.0
    print(f"Capacidad última: fuste {Qs:.0f} kN, punta {Qp:.0f} kN")
    print(f"  {'código':<6} {'tipo':<7} {'riesgo':<7} {'f_fuste':>7} {'f_punta':>7} {'Q_d [kN]':>9} {'a mano':>8}")
    for code, ptype, risk in (("EU", "driven", "medium"), ("EU", "bored", "medium"), ("US", "driven", "medium"),
                              ("US", "bored", "medium"), ("AU", "bored", "low"), ("AU", "bored", "high")):
        r = design_pile_capacity(PileCapacityInput(Q_shaft_ult_kN=Qs, Q_tip_ult_kN=Qp, pile_type=ptype,
                                                   geotechnical_risk=risk), code=code)
        hand = r.factor_shaft * Qs + r.factor_tip * Qp
        print(f"  {code:<6} {ptype:<7} {risk:<7} {r.factor_shaft:7.3f} {r.factor_tip:7.3f} {r.Q_design_kN:9.1f} {hand:8.1f}")
    print("  Los factores son los del módulo y no se han contrastado aquí con las tablas de cada norma; los 1,10/1,40 "
          "del perfil EU no son los γ_b/γ_s de la Tabla A.6/A.7 de EN 1997-1 sino un coeficiente único por tipo.\n")

    geo = MicropileGeometry(diameter_drilling=0.15, diameter_grouted=0.15, length_total=12.0, length_bond=8.0)
    m = micropile_capacity(geo, MicropileSoilType.SAND_GRAVEL)
    d_eff = max(0.15, 1.2 * 0.15)
    Rk = math.pi * d_eff * 8.0 * 80.0
    print(f"Micropilote: d_eff = max(0,15; 1,2·0,15) = {d_eff:.3f} m; R_k = π·{d_eff:.3f}·8·{m.q_s_used:.0f} = {Rk:.1f} kN "
          f"(paquete {m.R_skin_char:.1f}); R_d = {Rk:.1f}/(1,3·1,5) = {Rk / 1.95:.1f} kN (paquete {m.R_total_design:.1f})")
    for qs in (120.0, 200.0):
        mm = micropile_capacity(geo, MicropileSoilType.SAND_GRAVEL, q_s_kPa=qs)
        print(f"  con q_s = {qs:.0f} kPa (ensayo o práctica local): R_d = {mm.R_total_design:.1f} kN")
    print(f"\nGrupo de 6 micropilotes, N_d = 1400 kN, R_d por pilote {m.R_total_design:.1f} kN:")
    for sd in (2.0, 2.5, 3.0, 4.0):
        g = micropile_group_capacity(6, m.R_total_design, sd, 1400.0)
        print(f"  s/d = {sd}: E = {g.efficiency_E:.3f}, R_grupo = {g.R_group_design:.0f} kN, N/R = {g.utilization:.2f} "
              f"-> {'cumple' if g.ok else 'no cumple'}")
    for qs in (80.0, 120.0):
        Rd = micropile_capacity(geo, MicropileSoilType.SAND_GRAVEL, q_s_kPa=qs).R_total_design
        n = math.ceil(1400.0 / Rd)
        g = micropile_group_capacity(max(n, 2), Rd, 3.0, 1400.0)
        print(f"  Con q_s = {qs:.0f} kPa y s/d = 3 hacen falta {n} micropilotes (N/R = {g.utilization:.2f}).")
    print("Límites: q_s por defecto es el mínimo de la tabla del módulo (valores orientativos, no de Bustamante-Doix "
          "contrastados aquí); la eficiencia de grupo E = (s/d)/3 para s/d < 3 es una simplificación del módulo, "
          "no la fórmula de Converse-Labarre; sin resistencia por punta ni pandeo del micropilote.")


if __name__ == "__main__":
    main()
