"""Incrementos de tensión vertical de Boussinesq: carga puntual, lineal, faja, círculo y rectángulo, comprobados por integración numérica.

Cada solución cerrada del paquete (`analysis.stress`) se contrasta con un
método independiente dentro del ejemplo:
- faja flexible de 2 m (q = 100 kPa) frente a la integral de cargas lineales;
- círculo de radio 1,5 m frente a la integral de cargas puntuales en anillos;
- factor de Newmark bajo la esquina de un rectángulo frente a la integral
  doble de la carga puntual, y el valor de tabla I(m = n = 1) = 0,1752;
- dos implementaciones del paquete (`analysis.stress` y `analysis.boussinesq`).
También se compara el bulbo bajo una zapata de 2 × 3 m con la regla 2:1.

Antes de la 1.1.0 la faja usaba cos(2·θ1) en vez de cos(θ1 + θ2): bajo el eje,
a z = B, daba 0,448·q en lugar de 0,550·q.

Ejecutar:  python examples/boussinesq_point_line_strip_circle_rectangle_stress_vs_numerical_integration_and_newmark_values.py
"""
import math

import numpy as np

from foundationcalc.analysis.boussinesq import influence_corner
from foundationcalc.analysis.stress import (
    boussinesq_circular_load_centre, boussinesq_line_load_dsigma_z, boussinesq_point_load_dsigma_z,
    boussinesq_rect_centre, boussinesq_rect_point, boussinesq_strip_load_dsigma_z, newmark_influence_factor,
)


def main() -> None:
    P = 1000.0
    print(f"Carga puntual P = {P:.0f} kN: Δσ_z = 3·P·z³/(2·π·R⁵)")
    for z, r in ((1.0, 0.0), (2.0, 0.0), (2.0, 1.0), (4.0, 2.0)):
        hand = 3 * P * z ** 3 / (2 * math.pi * (r * r + z * z) ** 2.5)
        print(f"  z = {z} m, r = {r} m: {boussinesq_point_load_dsigma_z(P, r, 0.0, z):8.2f} kPa (a mano {hand:8.2f})")

    q, B, z = 100.0, 2.0, 2.0
    n = 20000
    xi = -B / 2 + (np.arange(n) + 0.5) * B / n
    print(f"\nFaja flexible B = {B} m, q = {q:.0f} kPa, z = {z} m (integración de {n} cargas lineales):")
    print(f"  {'x [m]':>6} {'paquete':>8} {'integral':>9} {'dif.':>9}")
    for x in (0.0, 0.5, 1.0, 2.0, 3.0):
        num = sum(boussinesq_line_load_dsigma_z(q * B / n, x - s, z) for s in xi)
        pk = boussinesq_strip_load_dsigma_z(q, B, x, z)
        print(f"  {x:6.1f} {pk:8.3f} {num:9.3f} {(pk / num - 1) * 100:+8.4f} %")
    print(f"  Bajo el eje: {boussinesq_strip_load_dsigma_z(q, B, 0.0, z) / q:.3f}·q (tabla de Das para z/b = 2: 0,550·q)")

    R = 1.5
    print(f"\nCírculo flexible R = {R} m, q = {q:.0f} kPa, bajo el centro (integral de anillos de carga puntual):")
    for zc in (0.5, 1.5, 3.0, 6.0):
        rr = (np.arange(4000) + 0.5) * R / 4000
        dA = 2 * math.pi * rr * (R / 4000)
        num = float(np.sum(3 * q * dA * zc ** 3 / (2 * math.pi * (rr ** 2 + zc ** 2) ** 2.5)))
        print(f"  z = {zc:3.1f} m: {boussinesq_circular_load_centre(q, R, zc):7.3f} kPa (integral {num:7.3f})")

    print("\nFactor de Newmark bajo la esquina, I(m, n) con m = B/z, n = L/z:")
    print(f"  {'m':>4} {'n':>4} {'stress':>8} {'boussinesq':>10} {'integral':>9}")
    for m_, n_ in ((1.0, 1.0), (0.5, 2.0), (2.0, 3.0), (0.2, 0.2)):
        g = 600
        xs = (np.arange(g) + 0.5) * m_ / g
        ys = (np.arange(g) + 0.5) * n_ / g
        X, Y = np.meshgrid(xs, ys)
        num = float(np.sum(3 / (2 * math.pi * (X ** 2 + Y ** 2 + 1) ** 2.5)) * (m_ / g) * (n_ / g))
        print(f"  {m_:4.1f} {n_:4.1f} {newmark_influence_factor(m_, n_, 1.0):8.4f} {influence_corner(m_, n_, 1.0):10.4f} {num:9.4f}")
    print("  Tabla de Newmark/Fadum: I(1, 1) = 0,1752.")

    Bf, Lf, qf = 2.0, 3.0, 200.0
    print(f"\nZapata {Bf} × {Lf} m con q = {qf:.0f} kPa: bajo el centro frente a la regla 2:1 (q·B·L/((B+z)(L+z))):")
    print(f"  {'z [m]':>5} {'Boussinesq':>10} {'2:1':>7} {'2:1/Bous.':>9} {'esquina':>8}")
    for zz in (0.5, 1.0, 2.0, 3.0, 5.0):
        b = boussinesq_rect_centre(qf, Bf, Lf, zz)
        s21 = qf * Bf * Lf / ((Bf + zz) * (Lf + zz))
        corner = boussinesq_rect_point(qf, Bf, Lf, zz, x_m=Bf / 2 - 1e-9, y_m=Lf / 2 - 1e-9)
        print(f"  {zz:5.1f} {b:10.1f} {s21:7.1f} {s21 / b:9.2f} {corner:8.1f}")
    print("  Cerca de la base la regla 2:1 infravalora el incremento bajo el centro; en profundidad converge.")


if __name__ == "__main__":
    main()
