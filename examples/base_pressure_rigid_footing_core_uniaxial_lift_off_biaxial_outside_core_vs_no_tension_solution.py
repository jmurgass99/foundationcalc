"""Presiones de contacto bajo una zapata rígida: núcleo central, despegue uniaxial, carga biaxial fuera del núcleo y vuelco.

Zapata de 3,0 × 2,0 m (L en X, B en Y) con N = 1200 kN centrado y momentos
crecientes. `BasePressureAnalysis` aplica Navier dentro del núcleo
(q = N/A·(1 ± 6·e_x/L ± 6·e_y/B)), el triángulo de despegue
(q_max = 2N/(3·B·(L/2 − e))) con excentricidad en un eje y marca el vuelco con
e ≥ L/2. Todo se comprueba a mano.

Con excentricidad biaxial fuera del núcleo el módulo vuelve a Navier y devuelve
una presión negativa: es un límite declarado. El ejemplo resuelve ese caso con
un método independiente (malla de la base, plano de presiones sin tracciones
ajustado por equilibrio con `scipy.optimize`) para medir cuánto se queda corta
la q_max de Navier.

Ejecutar:  python examples/base_pressure_rigid_footing_core_uniaxial_lift_off_biaxial_outside_core_vs_no_tension_solution.py
"""
import numpy as np
from scipy.optimize import fsolve

from foundationcalc import (
    BasePressureAnalysis, Column, CombinationEntry, LoadCombination, PointLoad, RectangularFoundation,
)


def no_tension_qmax(N, Mx, My, L, B, n=200):
    """Plano q = q0 + gx·x + gy·y recortado a q ≥ 0 que equilibra N, My (=Σq·x) y Mx (=Σq·y)."""
    x = (np.arange(n) + 0.5) / n * L - L / 2
    y = (np.arange(n) + 0.5) / n * B - B / 2
    X, Y = np.meshgrid(x, y)
    dA = (L / n) * (B / n)

    def res(p):
        q = np.maximum(p[0] + p[1] * X + p[2] * Y, 0.0)
        return [(q.sum() * dA - N) / N, ((q * X).sum() * dA - My) / N, ((q * Y).sum() * dA - Mx) / N]

    A = L * B
    p0 = [N / A, 12 * My / (B * L ** 3), 12 * Mx / (L * B ** 3)]
    p = fsolve(res, p0, xtol=1e-12)
    q = np.maximum(p[0] + p[1] * X + p[2] * Y, 0.0)
    return float(q.max()), float((q > 0).mean() * A), max(abs(v) for v in res(p))


def main() -> None:
    L, B, N = 3.0, 2.0, 1200.0
    fdn = RectangularFoundation(length=L * 1000, width=B * 1000, thickness=700)
    col = Column(length=500, width=500, pos_x=L * 500, pos_y=B * 500)
    bpa = BasePressureAnalysis(fdn, col)
    qa = N / (L * B)
    print(f"Zapata {L} × {B} m, N = {N:.0f} kN (sin peso propio), q_media = {qa:.1f} kPa; núcleo L/6 = {L / 6:.3f} m, B/6 = {B / 6:.3f} m\n")
    print(f"{'Caso':<28} {'e_x':>6} {'e_y':>6} {'régimen':<17} {'q_max':>8} {'q_min':>8} {'A_act':>6} {'q_max a mano':>12}")
    cases = [
        ("centrada", 0.0, 0.0),
        ("M_y = 300 (en el núcleo)", 0.0, 300.0),
        ("M_y = 900 (despegue en X)", 0.0, 900.0),
        ("M_x = 500 (despegue en Y)", 500.0, 0.0),
        ("M_x = 300, M_y = 700", 300.0, 700.0),
        ("M_y = 2000 (vuelco)", 0.0, 2000.0),
    ]
    for name, Mx, My in cases:
        combo = LoadCombination(name=name, entries=[CombinationEntry(load=PointLoad(fz=N, mx=Mx, my=My))])
        r = bpa.calculate_pressures(combo, include_self_weight=False)
        ex, ey = My / N, Mx / N
        if ex >= L / 2 or ey >= B / 2:
            hand = float("inf")
        elif 6 * ex / L + 6 * ey / B <= 1:
            hand = qa * (1 + 6 * ex / L + 6 * ey / B)
        elif ey == 0:
            hand = 2 * N / (3 * B * (L / 2 - ex))
        elif ex == 0:
            hand = 2 * N / (3 * L * (B / 2 - ey))
        else:
            hand = float("nan")
        hs = "∞" if hand == float("inf") else ("—" if hand != hand else f"{hand:.1f}")
        qmax = "∞" if r.q_max == float("inf") else f"{r.q_max:.1f}"
        print(f"{name:<28} {r.e_x:6.3f} {r.e_y:6.3f} {r.regime.value:<17} {qmax:>8} {r.q_min:8.1f} {r.active_area_m2:6.2f} {hs:>12}")

    Mx, My = 300.0, 700.0
    combo = LoadCombination(name="biaxial", entries=[CombinationEntry(load=PointLoad(fz=N, mx=Mx, my=My))])
    r = bpa.calculate_pressures(combo, include_self_weight=False)
    q_nt, A_c, err = no_tension_qmax(N, Mx, My, L, B)
    print(f"\nBiaxial fuera del núcleo (6·e_x/L + 6·e_y/B = {6 * My / N / L + 6 * Mx / N / B:.2f} > 1):")
    print(f"  Navier del paquete: q_max = {r.q_max:.1f} kPa y q_min = {r.q_min:.1f} kPa (tracción imposible en el contacto).")
    print(f"  Solución sin tracciones (malla 200 × 200, residuo {err:.1e}): q_max = {q_nt:.1f} kPa sobre {A_c:.2f} m² comprimidos.")
    lado = "inseguro" if q_nt > r.q_max else "seguro"
    print(f"  Navier da una q_max un {abs(1 - r.q_max / q_nt) * 100:.0f} % menor que la real: queda del lado {lado}, "
          "y su q_min negativa no tiene sentido físico. En este régimen hay que redimensionar o comprobar "
          "con el área eficaz de EN 1997-1, no con la presión de Navier.")

if __name__ == "__main__":
    main()
