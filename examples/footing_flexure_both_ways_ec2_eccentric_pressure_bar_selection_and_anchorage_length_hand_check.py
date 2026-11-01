"""Armado de flexión de una zapata aislada en las dos direcciones (EN 1992-1-1): presión excéntrica, barras y anclaje.

Zapata de 3,0 (L, en X) × 2,5 m (B) × 0,60 m, pilar de 40 × 40 cm,
N_Ed = 1800 kN y M_y = 270 kN·m (e_x = 0,15 m), C30/37, B500S, recubrimiento
50 mm, Ø16 preferente. `design_footing_flexure_both_ways`:
- toma la presión máxima de borde (Navier: q = N/A·(1 + 6e/L)) en las dos
  direcciones (conservador para la dirección corta);
- momento en la sección de referencia a 0,15·a dentro del pilar:
  M = q·b·v²/2 con v = (L − a)/2 + 0,15·a;
- A_s con z = d/2·(1 + √(1 − 3,53·K)) ≤ 0,95d y A_s,min = max(0,26·f_ctm/f_yk, 0,0013)·b·d;
- barras con s ≤ min(2,5h, 250 mm) y anclaje l_bd de EC2 §8.4 frente a la
  longitud recta del vuelo.
Todo se comprueba a mano en la dirección X.

Ejecutar:  python examples/footing_flexure_both_ways_ec2_eccentric_pressure_bar_selection_and_anchorage_length_hand_check.py
"""
import math

from foundationcalc import Concrete, ReinforcingSteel, anchorage_length_ec2, design_footing_flexure_both_ways


def main() -> None:
    L, B, h, N, My, a = 3.0, 2.5, 0.60, 1800.0, 270.0, 0.40
    C30, B500 = Concrete(fck=30), ReinforcingSteel(fyk=500)
    res = design_footing_flexure_both_ways(B_m=B, L_m=L, h_m=h, N_Ed_kN=N, My_Ed_kNm=My, cx_m=a, cy_m=a,
                                           concrete=C30, steel=B500, cover_mm=50.0, preferred_phi_mm=16.0)
    e = My / N
    q = N / (B * L) * (1 + 6 * e / L)
    v = (L - a) / 2 + 0.15 * a
    M = q * B * v ** 2 / 2
    d = h * 1000 - 50 - 8
    K = M * 1e6 / (B * 1000 * d ** 2 * 30)
    z = min(d / 2 * (1 + math.sqrt(1 - 3.53 * K)), 0.95 * d)
    As = M * 1e6 / (500 / 1.15 * z)
    fctm = 0.30 * 30 ** (2 / 3)
    Asmin = max(0.26 * fctm / 500, 0.0013) * B * 1000 * d
    print(f"Zapata {L} × {B} × {h} m, N = {N:.0f} kN, M_y = {My:.0f} kN·m -> e_x = {e:.3f} m (L/6 = {L / 6:.2f})")
    print(f"A mano (X): q_max = {N / (B * L):.1f}·(1 + 6·{e:.3f}/{L}) = {q:.1f} kPa; v = {v:.3f} m; "
          f"M = {q:.1f}·{B}·{v:.3f}²/2 = {M:.1f} kN·m")
    print(f"  d = {d:.0f} mm, K = {K:.4f}, z = {z:.1f} mm, A_s = {As:.0f} mm², A_s,min = {Asmin:.0f} mm²\n")

    print(f"{'dir.':<4} {'M_Ed':>7} {'A_s,req':>8} {'A_s,min':>8} {'barras':<16} {'A_s,disp':>8} {'l_bd':>6} {'l_disp':>6} {'estado':<14}")
    for k in ("X", "Y"):
        t = res[k]
        bars = f"{t.n_bars} Ø{t.bar_diameter_mm:.0f} @ {t.spacing_mm:.0f}"
        print(f"{k:<4} {t.M_Ed_kNm:7.1f} {t.As_req_mm2:8.0f} {t.As_min_mm2:8.0f} {bars:<16} {t.As_prov_mm2:8.0f} "
              f"{t.l_bd_mm:6.0f} {t.l_avail_mm:6.0f} {t.status:<14}")
    x = res["X"]
    print(f"Diferencia con la mano en X: M {x.M_Ed_kNm / M - 1:+.2e}, A_s {x.As_req_mm2 / As - 1:+.2e}")

    fctd = 0.7 * fctm / 1.5
    fbd = 2.25 * fctd
    lb = 16 / 4 * (500 / 1.15) / fbd
    lb_rqd, lbd = anchorage_length_ec2(16.0, 30.0, 500.0)
    print(f"\nAnclaje Ø16 en buena adherencia, σ_sd = f_yd: f_bd = 2,25·0,7·{fctm:.3f}/1,5 = {fbd:.3f} MPa; "
          f"l_b,rqd = (16/4)·{500 / 1.15:.1f}/{fbd:.3f} = {lb:.0f} mm (paquete {lb_rqd:.0f})")
    lb2, lbd2 = anchorage_length_ec2(16.0, 30.0, 500.0, As_req_mm2=x.As_req_mm2, As_prov_mm2=x.As_prov_mm2)
    print(f"  con σ_sd = f_yd·A_s,req/A_s,disp: l_bd = {lbd2:.0f} mm frente a {x.l_avail_mm:.0f} mm disponibles -> "
          f"{'patilla necesaria' if lbd2 > x.l_avail_mm else 'basta la longitud recta'}")
    print("Límites: q_max en las dos direcciones (en Y sobra armadura con excentricidad solo en X); sin comprobación de "
          "cortante en la sección a d de la cara; la separación máxima min(2,5h, 250 mm) es el criterio del módulo.")


if __name__ == "__main__":
    main()
