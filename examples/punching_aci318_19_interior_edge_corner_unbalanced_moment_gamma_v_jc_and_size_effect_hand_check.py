"""Punzonamiento según ACI 318-19 (§8.4.4.2 y §22.6) con transferencia de momento no equilibrado: pilar interior, de borde y de esquina.

v_u = V_u/A_c + γ_v·M_u·c/J_c, con perímetro crítico a d/2, γ_f = 1/(1 + ⅔·√(b1/b2)),
γ_v = 1 − γ_f y J_c del perímetro. Resistencia (Tabla 22.6.5.2, SI): la menor
de 0,33·λ_s·√f'c; 0,17·(1 + 2/β)·λ_s·√f'c; 0,083·(2 + α_s·d/b0)·λ_s·√f'c, con
λ_s = √(2/(1 + 0,004·d)) ≤ 1 y φ = 0,75.

Caso: pilar de 500 × 500 mm, d = 300 mm, V_u = 900 kN, M_u = 100 kN·m,
f'c = 30 MPa. Se comprueba el pilar interior a mano y se comparan las tres
posiciones; después se barre M_u hasta agotar.

Ejecutar:  python examples/punching_aci318_19_interior_edge_corner_unbalanced_moment_gamma_v_jc_and_size_effect_hand_check.py
"""
import math

from foundationcalc import punching_shear_aci318_check


def main() -> None:
    c, d, Vu, Mu, fc = 500.0, 300.0, 900.0, 100.0, 30.0
    b1 = b2 = c + d
    b0 = 2 * (b1 + b2)
    Ac = b0 * d
    gv = 1 - 1 / (1 + 2 / 3 * math.sqrt(b1 / b2))
    Jc = d * b1 ** 3 / 6 + b1 * d ** 3 / 6 + d * b2 * b1 ** 2 / 2
    v_dir = Vu * 1e3 / Ac
    v_mom = gv * Mu * 1e6 * (b1 / 2) / Jc
    lam_s = min(math.sqrt(2 / (1 + 0.004 * d)), 1.0)
    vc = min(0.33 * lam_s * math.sqrt(fc), 0.17 * 3 * lam_s * math.sqrt(fc),
             0.083 * (2 + 40 * d / b0) * lam_s * math.sqrt(fc))
    print(f"Pilar interior {c:.0f} × {c:.0f} mm, d = {d:.0f} mm, V_u = {Vu:.0f} kN, M_u = {Mu:.0f} kN·m, f'c = {fc:.0f} MPa")
    print(f"A mano: b0 = {b0:.0f} mm, A_c = {Ac:.0f} mm², γ_v = {gv:.3f}, J_c = {Jc:.4e} mm⁴")
    print(f"  v = {v_dir:.4f} + {v_mom:.4f} = {v_dir + v_mom:.4f} MPa; λ_s = {lam_s:.4f}; v_c = {vc:.4f} MPa; "
          f"φ·v_c = {0.75 * vc:.4f} MPa -> {(v_dir + v_mom) / (0.75 * vc):.3f}")
    r = punching_shear_aci318_check(c, c, d, Vu, fc, Mux_kNm=Mu)
    print(f"Paquete: v_ug,max = {r.v_ug_max_MPa:.4f} MPa, φ·v_c = {r.phi_vc_MPa:.4f} MPa, DCR = {r.utilization:.3f} "
          f"({'cumple' if r.is_ok else 'no cumple'})\n")

    print(f"{'posición':<9} {'b0 [mm]':>8} {'γ_vx':>6} {'v_dir':>6} {'v_mom':>6} {'φv_c':>6} {'DCR':>6}")
    for pos in ("interior", "edge", "corner"):
        rr = punching_shear_aci318_check(c, c, d, Vu, fc, Mux_kNm=Mu, column_type=pos)
        print(f"{pos:<9} {rr.b0_mm:8.0f} {rr.gamma_vx:6.3f} {rr.v_dir_MPa:6.3f} {rr.v_mom_x_MPa:6.3f} {rr.phi_vc_MPa:6.3f} {rr.utilization:6.3f}")
    worst = max(("interior", "edge", "corner"),
                key=lambda p: punching_shear_aci318_check(c, c, d, Vu, fc, Mux_kNm=Mu, column_type=p).utilization)
    print(f"Con las mismas cargas la peor posición es «{worst}»: el perímetro se reduce a 3 o 2 lados.\n")

    print("Barrido del momento (pilar interior):")
    lim = None
    for M in (0.0, 100.0, 200.0, 300.0, 400.0, 500.0):
        rr = punching_shear_aci318_check(c, c, d, Vu, fc, Mux_kNm=M)
        print(f"  M_u = {M:5.0f} kN·m: v_max = {rr.v_ug_max_MPa:.3f} MPa, DCR = {rr.utilization:.3f}")
        if lim is None and rr.utilization > 1:
            lim = M
    print(f"  Primer momento del barrido que agota: {lim:.0f} kN·m." if lim is not None else "  Ninguno agota.")
    print("Límites: el perímetro de borde y esquina se toma con el borde libre normal a X; sin armadura de "
          "punzonamiento; el momento sobre Y se suma con el mismo criterio (v_max en la esquina más cargada).")


if __name__ == "__main__":
    main()
