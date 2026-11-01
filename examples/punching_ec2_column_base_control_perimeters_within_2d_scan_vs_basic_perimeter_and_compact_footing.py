"""Punzonamiento de una base de pilar según EN 1992-1-1 §6.4.4(2): barrido de perímetros a ≤ 2d frente al perímetro básico a 2d.

En una zapata la reacción del terreno dentro del perímetro de control descuenta
fuerza (V_Ed,red = V_Ed − ΔV_Ed) y la resistencia crece con 2d/a (ec. 6.50):
    v_Ed(a) = β·N·(1 − A_u(a)/A_zapata)/(u(a)·d)
    v_Rd(a) = max(C_Rd,c·k·(100·ρ_l·f_ck)^(1/3), v_min)·2d/a
con u(a) = 2(c1 + c2) + 2πa y A_u(a) = c1·c2 + 2(c1 + c2)·a + π·a². El crítico
se busca entre 0,1d y 2d (EC2 §6.4.2(2): en cimentaciones hay que comprobar
perímetros más cercanos que 2d). Hasta la 1.1.0 la rama de zapata «estándar»
solo miraba a = 2d.

Casos: zapata de 3 × 3 m con pilar central de 40 × 40 cm, d = 0,50 m,
N_Ed = 800 kN, C25/30, ρ = 0,5 %; la misma con N = 2500 kN; una zapata
compacta de 1,4 × 1,4 m (el perímetro a 2d se sale de la planta); y el pilar
en borde y en esquina (β = 1,4 y 1,5).

Ejecutar:  python examples/punching_ec2_column_base_control_perimeters_within_2d_scan_vs_basic_perimeter_and_compact_footing.py
"""
import math

from foundationcalc import Column, RectangularFoundation, punching_shear_check


def v_ratio(a, c, d, N, Af, beta, vrd):
    u = 4 * c + 2 * math.pi * a
    A = c * c + 4 * c * a + math.pi * a * a
    return beta * N * (1 - A / Af) / (u * d) / (vrd * 2 * d / a)


def main() -> None:
    c, d, fck, rho = 0.40, 0.50, 25.0, 0.005
    k = min(1 + math.sqrt(200 / (d * 1000)), 2.0)
    vrd = max(0.18 / 1.5 * k * (100 * rho * fck) ** (1 / 3), 0.035 * k ** 1.5 * math.sqrt(fck)) * 1000
    print(f"k = {k:.4f}; v_Rd,c = max(0,12·k·(100ρ·fck)^(1/3), v_min) = {vrd:.1f} kPa\n")

    L, N = 3.0, 800.0
    fdn = RectangularFoundation(length=L * 1000, width=L * 1000, thickness=600)
    col = Column(length=c * 1000, width=c * 1000, pos_x=L * 500, pos_y=L * 500)
    r = punching_shear_check(fdn, col, N, fck, rho, rho, d)
    print(f"Zapata {L} × {L} m, N = {N:.0f} kN, pilar interior (β = {r.beta}):")
    print(f"  {'a/d':>5} {'a [m]':>6} {'u [m]':>6} {'F_red [kN]':>10} {'v_Ed [kPa]':>10} {'v_Rd·2d/a':>9} {'v_Ed/v_Rd':>9}")
    for f in (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
        a = f * d
        u = 4 * c + 2 * math.pi * a
        A = c * c + 4 * c * a + math.pi * a * a
        F = N * (1 - A / L ** 2)
        print(f"  {f:5.2f} {a:6.3f} {u:6.3f} {F:10.1f} {1.15 * F / (u * d):10.1f} {vrd * 2 * d / a:9.1f} "
              f"{v_ratio(a, c, d, N, L * L, 1.15, vrd):9.3f}")
    old = v_ratio(2 * d, c, d, N, L * L, 1.15, vrd)
    print(f"  Paquete: gobierna a = {r.a_crit_m:.3f} m (a/d = {r.a_crit_m / d:.2f}), u = {r.u1:.3f} m, "
          f"v_Ed = {r.tau_sd:.1f} kPa, v_Rd(a) = {r.tau_rd_scaled_kPa:.1f} kPa -> {r.utilization:.3f} ({r.verdict})")
    print(f"  Comprobación a mano en ese a: {v_ratio(r.a_crit_m, c, d, N, L * L, 1.15, vrd):.4f}. Solo a 2d (antes): "
          f"{old:.3f}; el perímetro crítico da un {(r.utilization / old - 1) * 100:.0f} % más de utilización.\n")

    print("Otros casos:")
    for name, Lf, Nn, px, py in (
        ("3 × 3 m, N = 2500 kN, interior", 3.0, 2500.0, 1500, 1500),
        ("compacta 1,4 × 1,4 m, N = 600 kN", 1.4, 600.0, 700, 700),
        ("3 × 3 m, N = 800 kN, pilar en borde", 3.0, 800.0, 200, 1500),
        ("3 × 3 m, N = 800 kN, pilar en esquina", 3.0, 800.0, 200, 200),
    ):
        f2 = RectangularFoundation(length=Lf * 1000, width=Lf * 1000, thickness=600)
        c2 = Column(length=c * 1000, width=c * 1000, pos_x=px, pos_y=py)
        rr = punching_shear_check(f2, c2, Nn, fck, rho, rho, d)
        print(f"  {name:<38} β = {rr.beta:4.2f}, compacta {'sí' if rr.is_compact else 'no'}, a = {rr.a_crit_m:.3f} m, "
              f"v_Ed/v_Rd = {rr.utilization:.3f} -> {rr.verdict}")
    print("Límites: presión del terreno uniforme N/A (sin momento) y perímetro de pilar interior aunque el pilar esté en "
          "borde o esquina: β (1,4/1,5) es la única corrección; sin armadura de punzonamiento.")


if __name__ == "__main__":
    main()
