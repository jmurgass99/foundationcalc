"""Asiento elástico inmediato de un rectángulo flexible sobre semiespacio: factor I_s de esquina y de centro frente a la integración numérica.

s = q·B·(1 − ν²)/E·I_s con B el lado corto y m = L/B (Steinbrenner/Schleicher,
espesor infinito, Bowles 1996):
    I_s,esquina = (1/π)·[m·ln((1 + √(1+m²))/m) + ln(m + √(1+m²))]
    I_s,centro  = 2·I_s,esquina (cuatro rectángulos B/2 × L/2)
Comprobación independiente: el asiento de una carga puntual en superficie es
w = P·(1 − ν²)/(π·E·r), así que I_s,esquina = (1/(π·B))·∬ dA/r; se integra
con una malla de 400 × 400. Valores de tabla: cuadrado 1,12 (centro) y 0,56
(esquina); L/B = 2: 1,53 / 0,77.

Antes de la 1.1.0 los dos términos tenían el factor m y los logaritmos
cruzados: coincidía en el cuadrado pero con L/B = 2 daba 2,14 (+40 % sobre el
centro) y con L/B = 5, 7,49 (+256 %).

Caso de aplicación: zapata de 2 × 3 m con q = 150 kPa sobre arena (E = 25 MPa,
ν = 0,3).

Ejecutar:  python examples/elastic_settlement_steinbrenner_influence_factor_corner_centre_vs_numerical_integration_l_over_b_1_to_10.py
"""
import math

import numpy as np

from foundationcalc.analysis.consolidation import elastic_settlement_rectangle


def I_corner_numeric(m: float, n: int = 400) -> float:
    x = (np.arange(n) + 0.5) / n
    y = (np.arange(n) + 0.5) * m / n
    X, Y = np.meshgrid(x, y)
    return float(np.sum(1.0 / np.hypot(X, Y)) * (1.0 / n) * (m / n) / math.pi)


def main() -> None:
    difs = []
    print(f"{'L/B':>5} {'esquina':>8} {'integral':>9} {'centro':>8} {'2×integral':>10} {'fórmula anterior':>16}")
    for m in (1.0, 1.5, 2.0, 3.0, 5.0, 10.0):
        c = elastic_settlement_rectangle(1.0, 1.0, m, 1.0, nu=0.0, location="corner")
        k = elastic_settlement_rectangle(1.0, 1.0, m, 1.0, nu=0.0)
        num = I_corner_numeric(m)
        difs.append(1 - num / c)
        s1 = math.sqrt(1 + m * m)
        old = (1 / math.pi) * (m * math.log((s1 + m) / (s1 - m)) + math.log((s1 + 1) / (s1 - 1)))
        print(f"{m:5.1f} {c:8.4f} {num:9.4f} {k:8.4f} {2 * num:10.4f} {old:16.4f}")
    print(f"La integral de malla queda entre {min(difs) * 100:.2f} % y {max(difs) * 100:.2f} % por debajo de la fórmula "
          "(la singularidad 1/r de la esquina se integra con error de malla); la fórmula anterior solo acertaba en L/B = 1.\n")

    q, B, L, E, nu = 150.0, 2.0, 3.0, 25000.0, 0.3
    s_c = elastic_settlement_rectangle(q, B, L, E, nu=nu) * 1000
    s_e = elastic_settlement_rectangle(q, B, L, E, nu=nu, location="corner") * 1000
    m = L / B
    s1 = math.sqrt(1 + m * m)
    I_c = 2 / math.pi * (m * math.log((1 + s1) / m) + math.log(m + s1))
    print(f"Zapata flexible {B} × {L} m, q = {q:.0f} kPa, E = {E / 1000:.0f} MPa, ν = {nu}:")
    print(f"  a mano: I_s,centro = {I_c:.4f}; s = {q:.0f}·{B}·(1 − {nu}²)/{E:.0f}·{I_c:.4f} = {q * B * (1 - nu ** 2) / E * I_c * 1000:.2f} mm")
    print(f"  paquete: centro {s_c:.2f} mm, esquina {s_e:.2f} mm (la esquina es la mitad del centro: {s_e / s_c:.3f}).")
    print("Límite: semiespacio homogéneo de espesor infinito; con un estrato rígido a poca profundidad el asiento es "
          "menor (factores de Steinbrenner con H/B, no implementados aquí).")


if __name__ == "__main__":
    main()
