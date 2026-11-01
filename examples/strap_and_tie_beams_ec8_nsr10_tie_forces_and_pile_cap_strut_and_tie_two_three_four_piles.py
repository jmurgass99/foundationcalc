"""Vigas centradoras y de atado (fuerzas sísmicas EC8 y NSR-10) y encepados de 2, 3 y 4 pilotes por bielas y tirantes.

1) Viga centradora entre una zapata de medianera (N1 = 1200 kN, excentricidad
   0,40 m) y una interior (N2 = 1800 kN) a 6 m: `strap_for_two_footings`
   (T = 0,03·ΣN, M = N_max·e + q·L²/12, V = M/L, canto ≥ L/12 y 350 mm).
2) Viga de atado: fuerza ±k·α·S·N_Ed según el tipo de terreno (k = 0,3/0,4/0,6
   para B/C/D, tal como lo trae `seismic_tie_force`) y NSR-10 A.3.6.4.2
   (T = 0,25·A_a·P, coeficiente único, P de servicio del elemento más cargado).
3) Encepados con las fórmulas de bielas y tirantes del módulo (tipo EHE):
   2 pilotes T = N_d·(v + 0,25a)/(0,85d); 3 pilotes T = 0,68·(N_d/d)·(0,58l − 0,25a);
   4 pilotes T = N_d/(0,85d)·(0,5l − 0,25a) por dirección; f_yd ≤ 400 MPa.
   Se recalculan a mano y se reparten las cargas de pilote con el encepado
   rígido (F_i = V/n + M·y_i/Σy²).

Ejecutar:  python examples/strap_and_tie_beams_ec8_nsr10_tie_forces_and_pile_cap_strut_and_tie_two_three_four_piles.py
"""
from foundationcalc import (
    GroundType, ReinforcingSteel, cap_four_piles, cap_three_piles, cap_two_piles, distribute_forces_rigid_cap,
    seismic_tie_force, strap_for_two_footings, tie_beam_minimum_dimensions,
)
from foundationcalc.design.strap_beam import design_tie_beam_nsr10


def main() -> None:
    N1, N2, L, e, q = 1200.0, 1800.0, 6000.0, 400.0, 10.0
    s = strap_for_two_footings(N1, N2, L, eccentricity_mm=e, q_self_kNm=q)
    M = max(N1, N2) * e / 1000 + q * (L / 1000) ** 2 / 12
    print(f"Viga centradora: N1 = {N1:.0f}, N2 = {N2:.0f} kN, L = {L / 1000:.0f} m, e = {e / 1000} m")
    print(f"  a mano: T = 0,03·{N1 + N2:.0f} = {0.03 * (N1 + N2):.0f} kN; M = {max(N1, N2):.0f}·{e / 1000} + {q}·{L / 1000:.0f}²/12 "
          f"= {M:.0f} kN·m; V = M/L = {M / (L / 1000):.0f} kN; canto = max(L/12, 350) = {max(L / 12, 350):.0f} mm")
    print(f"  paquete: T = {s.design_axial_kN:.0f} kN, M = {s.design_moment_kNm:.0f} kN·m, V = {s.design_shear_kN:.0f} kN, "
          f"{s.width_mm:.0f} × {s.depth_mm:.0f} mm")
    print("  Nota: M toma la mayor de las dos cargas por la excentricidad; con la medianera en el pilar 1 la "
          f"excentricidad la produce N1 ({N1 * e / 1000:.0f} kN·m): el módulo queda del lado conservador.\n")

    Ned, aS = 1800.0, 0.30
    print(f"Viga de atado, N_Ed = {Ned:.0f} kN, α·S = {aS}:")
    for g in (GroundType.A, GroundType.B, GroundType.C, GroundType.D):
        print(f"  terreno {g.value}: ±{seismic_tie_force(Ned, aS, g):.0f} kN")
    for n in (3, 5):
        b, h = tie_beam_minimum_dimensions(n)
        print(f"  {n} plantas sobre el sótano: sección mínima {b:.0f} × {h:.0f} mm")
    r = design_tie_beam_nsr10(Pu_col_max_kN=1800.0, Aa=0.25, length_m=6.0)
    print(f"  NSR-10 A.3.6.4.2: T = 0,25·{r.Aa}·{r.Pu_col_max_kN:.0f} = {r.axial_force_Tu_kN:.1f} kN; "
          f"{r.width_mm:.0f} × {r.depth_mm:.0f} mm, A_s = max({r.As_tension_mm2:.0f}, {r.As_min_mm2:.0f}) -> "
          f"{r.n_bars} barras de Ø{r.bar_diameter_mm} ({r.As_provided_mm2:.0f} mm²)\n")

    steel = ReinforcingSteel(fyk=500)
    fyd = min(500 / 1.15, 400.0)
    Nd, a, d = 1500.0, 500.0, 900.0
    v, l3, l4 = 750.0, 1800.0, 1800.0
    t2 = cap_two_piles(Nd, v_mm=v, a_mm=a, d_mm=d, steel=steel)
    t3 = cap_three_piles(Nd * 2, l_mm=l3, a_mm=a, d_mm=d, steel=steel)
    t4x, t4y = cap_four_piles(Nd * 2, l1_mm=l4, l2_mm=l4, a1_mm=a, a2_mm=a, d_mm=d, steel=steel)
    print(f"Encepados (f_yd limitado a {fyd:.0f} MPa, a = {a:.0f} mm, d = {d:.0f} mm):")
    print(f"  2 pilotes, N_d = {Nd:.0f} kN, v = {v:.0f} mm: T = {Nd:.0f}·({v:.0f} + 0,25·{a:.0f})/(0,85·{d:.0f}) = "
          f"{Nd * (v + 0.25 * a) / (0.85 * d):.1f} kN (paquete {t2.T_d / 1000:.1f}); A_s = {t2.A_s:.0f} mm²")
    print(f"  3 pilotes, N_d = {2 * Nd:.0f} kN, l = {l3:.0f} mm: T = 0,68·{2 * Nd:.0f}/{d:.0f}·(0,58·{l3:.0f} − 0,25·{a:.0f}) = "
          f"{0.68 * 2 * Nd / d * (0.58 * l3 - 0.25 * a):.1f} kN (paquete {t3.T_d / 1000:.1f}); A_s = {t3.A_s:.0f} mm²")
    print(f"  4 pilotes, N_d = {2 * Nd:.0f} kN, l = {l4:.0f} mm: T = {2 * Nd:.0f}/(0,85·{d:.0f})·(0,5·{l4:.0f} − 0,25·{a:.0f}) = "
          f"{2 * Nd / (0.85 * d) * (0.5 * l4 - 0.25 * a):.1f} kN por dirección (paquete {t4x.T_d / 1000:.1f}, {t4y.T_d / 1000:.1f})")
    piles = [(-0.9, -0.9), (0.9, -0.9), (-0.9, 0.9), (0.9, 0.9)]
    F = distribute_forces_rigid_cap(3000.0, 400.0, 250.0, piles)
    print(f"  Reparto rígido de V = 3000 kN, M_x = 400, M_y = 250 kN·m en 4 pilotes a ±0,9 m: "
          + ", ".join(f"{f:.1f}" for f in F)
          + f" kN (a mano 750 ± 400·0,9/3,24 ± 250·0,9/3,24 = 750 ± {400 * 0.9 / 3.24:.1f} ± {250 * 0.9 / 3.24:.1f})")
    print("Límites: las fórmulas de encepado y la de zapata rígida (`strut_and_tie_rigid_footing`) se toman tal como "
          "las trae el módulo, con la definición de N_d y v de cada una, y no se han contrastado aquí con la EHE-08; "
          "los coeficientes 0,3/0,4/0,6 y las secciones mínimas de EC8 tampoco.")


if __name__ == "__main__":
    main()
