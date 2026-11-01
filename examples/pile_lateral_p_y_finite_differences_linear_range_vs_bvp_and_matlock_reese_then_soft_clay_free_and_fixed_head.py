"""Pilote con carga lateral por curvas p-y y diferencias finitas: validación en rango lineal y pilote en arcilla blanda con cabeza libre y encepada.

`solve_pile_lateral` resuelve EI·y'''' + p(y) = 0 con diferencias finitas y
rigidez secante iterada. Validación con un método independiente: con cargas
diminutas la curva de Reese en arena es lineal, p = k·z·y, y el problema es
EI·y'''' + k·z·y = 0, que se resuelve aquí con `scipy.integrate.solve_bvp`;
además se comparan con los coeficientes de Matlock y Reese para pilote largo
(y0 = 2,435·H·T³/EI + 1,623·M·T²/EI; encepado y0 = 0,93·H·T³/EI y
M0 = −0,93·H·T, con T = (EI/k)^(1/5)).

Hasta la 1.1.0 la cabeza encepada ignoraba H (desplazamiento nulo) y con
momento en cabeza el resultado dependía de la malla.

Caso de aplicación: pilote de Ø0,8 m y 20 m (EI = 600 MN·m²) en arcilla blanda
(c_u = 30 kPa, γ' = 8 kN/m³, ε50 = 0,02, Matlock) con H = 150 kN.

Ejecutar:  python examples/pile_lateral_p_y_finite_differences_linear_range_vs_bvp_and_matlock_reese_then_soft_clay_free_and_fixed_head.py
"""
import numpy as np
from scipy.integrate import solve_bvp

from foundationcalc.analysis.pile_lateral import PileLateral, PYSoilLayer, PYType, solve_pile_lateral


def bvp(H, M, fixed, EI, k, L):
    def f(z, Y):
        return np.vstack([Y[1], Y[2], Y[3], -k * z * Y[0] / EI])

    def bc(a, b):
        head = [a[1], EI * a[3] - H] if fixed else [EI * a[2] - M, EI * a[3] - H]
        return np.array(head + [b[2], b[3]])

    z = np.linspace(0, L, 201)
    sol = solve_bvp(f, bc, z, np.zeros((4, z.size)), tol=1e-8, max_nodes=20000)
    Y = sol.sol(np.array([0.0]))
    return float(Y[0][0]), float(EI * Y[2][0])


def main() -> None:
    EI, k, L = 200000.0, 20000.0, 20.0
    T = (EI / k) ** 0.2
    print(f"Validación lineal: EI = {EI:.0f} kN·m², k = {k:.0f} kN/m³ (Reese en arena con cargas diminutas), L = {L} m, "
          f"T = {T:.4f} m, L/T = {L / T:.1f}")
    print(f"  {'caso':<26} {'y0 FD [m]':>11} {'y0 BVP [m]':>11} {'Matlock-Reese':>13} {'M0 FD':>9} {'M0 BVP':>9}")
    for name, H, M, fixed, mr in (
        ("cabeza libre, H = 0,01", 0.01, 0.0, False, 2.435 * 0.01 * T ** 3 / EI),
        ("cabeza libre, M = 0,01", 0.0, 0.01, False, 1.623 * 0.01 * T ** 2 / EI),
        ("encepado, H = 0,01", 0.01, 0.0, True, 0.93 * 0.01 * T ** 3 / EI),
    ):
        pile = PileLateral(length_m=L, diameter_m=0.6, EI_kNm2=EI, head_load_H_kN=H, head_moment_M_kNm=M, fixed_head=fixed,
                           layers=[PYSoilLayer(z_top_m=0, z_bot_m=L, py_type=PYType.REESE_SAND, phi_deg=35.0,
                                               gamma_eff_kN_m3=10.0, k_pa_per_m=k)])
        r = solve_pile_lateral(pile, n_segments=200, max_iter=300, tol_mm=1e-6)
        y0, M0 = bvp(H, M, fixed, EI, k, L)
        print(f"  {name:<26} {r.y_m[0]:11.4e} {y0:11.4e} {mr:13.4e} {r.M_kNm[0]:9.5f} {M0:9.5f}")
    print(f"  M0 del encepado según Matlock y Reese: −0,93·H·T = {-0.93 * 0.01 * T:.5f} kN·m\n")

    D, EIc = 0.8, 600000.0
    clay = [PYSoilLayer(z_top_m=0.0, z_bot_m=20.0, py_type=PYType.MATLOCK_SOFT_CLAY, c_u_kPa=30.0,
                        gamma_eff_kN_m3=8.0, eps_50=0.02, J=0.5)]
    print(f"Pilote Ø{D} m, 20 m, EI = {EIc:.0f} kN·m² en arcilla blanda (Matlock, c_u = 30 kPa), H = 150 kN:")
    for fixed in (False, True):
        p = PileLateral(length_m=20.0, diameter_m=D, EI_kNm2=EIc, layers=clay, head_load_H_kN=150.0, fixed_head=fixed)
        r = solve_pile_lateral(p, n_segments=160, max_iter=200, tol_mm=1e-3)
        iM = int(np.argmax(np.abs(r.M_kNm)))
        zero = next((r.z[i] for i in range(1, len(r.y_m)) if r.y_m[i] * r.y_m[0] < 0), None)
        print(f"  {'encepado' if fixed else 'libre':<8}: y0 = {r.y_head_mm:6.1f} mm, |M|max = {r.M_max_kNm:6.1f} kN·m a "
              f"{r.z[iM]:4.1f} m, M en cabeza = {r.M_kNm[0]:7.1f} kN·m, primer cero de y a "
              f"{zero:.1f} m, p máx = {np.abs(r.p_kN_per_m).max():5.1f} kN/m")
    z1 = 2.0
    pu = min((3 + 8 * z1 / 30 + 0.5 * z1 / D) * 30 * D, 9 * 30 * D)
    print(f"  Resistencia última de Matlock a 2 m: p_u = (3 + γ'z/c_u + J·z/D)·c_u·D = {pu:.1f} kN/m (tope 9·c_u·D = {9 * 30 * D:.0f})")
    print("Límites: curvas API en arena con A = 0,9 (cíclica) siempre y k aproximado; la curva de Reese es la "
          "envolvente hiperbólica simplificada; API en arcilla cíclica con reducción lineal propia del módulo.")


if __name__ == "__main__":
    main()
