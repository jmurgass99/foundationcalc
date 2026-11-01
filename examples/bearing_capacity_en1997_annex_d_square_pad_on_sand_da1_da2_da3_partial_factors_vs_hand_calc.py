"""Capacidad portante drenada de una zapata cuadrada en arena según EN 1997-1 Anexo D, con los enfoques DA1-C1, DA1-C2, DA2 y DA3.

Zapata de 2,5 × 2,5 m apoyada a 1,0 m en arena (φ'k = 32°, c' = 0, γ = 19 kN/m³),
cargas centradas Gk = 1000 kN y Qk = 400 kN. Para cada enfoque se toman los
coeficientes de EN 1997-1 Anexo A (A1/A2, M1/M2, R1/R2/R3) con
`get_partial_factors`, se calcula R_d con `drained_bearing_capacity` y se compara
con la acción de cálculo V_d. El enfoque que gobierna se elige por cálculo.

Comprobación a mano dentro del ejemplo (Anexo D.4, con φ'k):
  N_q = e^(π·tan φ)·tan²(45° + φ/2), N_γ = 2·(N_q − 1)·tan φ (base rugosa),
  s_q = 1 + (B'/L')·sen φ, s_γ = 1 − 0,3·B'/L',
  q_ult = q'·N_q·s_q + ½·γ'·B'·N_γ·s_γ.

Ejecutar:  python examples/bearing_capacity_en1997_annex_d_square_pad_on_sand_da1_da2_da3_partial_factors_vs_hand_calc.py
"""
import math

from foundationcalc import (
    DesignApproach, LimitState, NationalAnnex, RectangularFoundation, SoilLayer, SoilType,
    drained_bearing_capacity, get_partial_factors,
)


def d_phi(tan_phi_k: float, gamma_phi: float = 1.25) -> float:
    return math.degrees(math.atan(tan_phi_k / gamma_phi))


def main() -> None:
    B, D, phi, gamma = 2.5, 1.0, 32.0, 19.0
    Gk, Qk = 1000.0, 400.0
    fdn = RectangularFoundation(length=B * 1000, width=B * 1000, thickness=600, embedment_depth=D * 1000)
    sand = SoilLayer(name="arena densa", thickness=10, soil_type=SoilType.COHESIONLESS,
                     friction_angle=phi, cohesion=0.0, unit_weight=gamma)

    # --- Comprobación a mano con valores característicos -------------------
    t = math.tan(math.radians(phi))
    Nq = math.exp(math.pi * t) * math.tan(math.radians(45 + phi / 2)) ** 2
    Ng = 2 * (Nq - 1) * t
    sq, sg = 1 + math.sin(math.radians(phi)), 0.7
    q_hand = gamma * D * Nq * sq + 0.5 * gamma * B * Ng * sg
    rk = drained_bearing_capacity(fdn, sand)
    print(f"Zapata {B} × {B} m a D = {D} m; arena φ'k = {phi}°, γ = {gamma} kN/m³; Gk = {Gk:.0f} kN, Qk = {Qk:.0f} kN")
    print(f"A mano: N_q = {Nq:.3f}, N_γ = {Ng:.3f}, s_q = {sq:.4f}, s_γ = {sg}; "
          f"q_ult = {gamma * D:.1f}·{Nq:.2f}·{sq:.3f} + ½·{gamma}·{B}·{Ng:.2f}·{sg} = {q_hand:.1f} kPa")
    print(f"Paquete: N_q = {rk.Nq:.3f}, N_γ = {rk.Ngamma:.3f}, q_ult = {rk.q_ult:.1f} kPa "
          f"(diferencia {(rk.q_ult / q_hand - 1) * 100:+.4f} %)\n")

    # --- Los cuatro enfoques -------------------------------------------------
    print(f"{'Enfoque':<8} {'γG':>5} {'γQ':>5} {'γφ':>5} {'γRv':>5} {'φd [°]':>7} {'q_ult [kPa]':>11} "
          f"{'R_d [kN]':>9} {'V_d [kN]':>9} {'V_d/R_d':>8}")
    rows = []
    for da in (DesignApproach.DA1_C1, DesignApproach.DA1_C2, DesignApproach.DA2, DesignApproach.DA3):
        pf = get_partial_factors(da, LimitState.GEO)
        Vd = pf.actions.gamma_G_unfav * Gk + pf.actions.gamma_Q_unfav * Qk
        r = drained_bearing_capacity(fdn, sand, V_load=Vd, gamma_Rv=pf.resistance.gamma_Rv,
                                     gamma_phi=pf.soil.gamma_phi, gamma_c=pf.soil.gamma_c)
        rows.append((da.value, Vd / r.R_d, r.q_ult, Vd))
        print(f"{da.value:<8} {pf.actions.gamma_G_unfav:5.2f} {pf.actions.gamma_Q_unfav:5.2f} {pf.soil.gamma_phi:5.2f} "
              f"{pf.resistance.gamma_Rv:5.2f} {r.phi_d_deg:7.2f} {r.q_ult:11.1f} {r.R_d:9.0f} {Vd:9.0f} {Vd / r.R_d:8.3f}")
    gov = max(rows, key=lambda x: x[1])
    print(f"\nGobierna {gov[0]} con V_d/R_d = {gov[1]:.3f}: "
          + ("la zapata cumple en los cuatro enfoques." if gov[1] <= 1 else "la zapata no cumple; hay que agrandarla."))
    d = {name: (u, q, v) for name, u, q, v in rows}
    verbo = "supera a" if d["DA1-C2"][0] > d["DA1-C1"][0] else "queda por debajo de"
    print(f"DA1-C2 reduce φ a {d_phi(t):.2f}°: q_ult pasa a {d['DA1-C2'][1] / d['DA1-C1'][1]:.2f} veces el de "
          f"DA1-C1, mientras la acción solo baja a {d['DA1-C2'][2] / d['DA1-C1'][2]:.2f} veces; por eso su relación "
          f"({d['DA1-C2'][0]:.3f}) {verbo} la de DA1-C1 ({d['DA1-C1'][0]:.3f}).")

    # --- Anejo nacional español (perfil del paquete) -----------------------
    pf_es = get_partial_factors(DesignApproach.DA2, LimitState.GEO, annex=NationalAnnex.SPAIN)
    Vd = pf_es.actions.gamma_G_unfav * Gk + pf_es.actions.gamma_Q_unfav * Qk
    r_es = drained_bearing_capacity(fdn, sand, gamma_Rv=pf_es.resistance.gamma_Rv)
    print(f"\nPerfil SPAIN del paquete (DA2, γ_R;v = {pf_es.resistance.gamma_Rv}): R_d = {r_es.R_d:.0f} kN, "
          f"V_d/R_d = {Vd / r_es.R_d:.3f}. El valor 2,15 está tomado tal como lo trae el módulo "
          "y no se ha contrastado aquí con el anejo nacional.")
    print("Límites: un solo estrato en la cota de apoyo, sin nivel freático (γ' = γ) y sin factores de profundidad, "
          "como el Anexo D; para perfiles estratificados, `multi_layer_bearing_capacity` (heurística declarada).")


if __name__ == "__main__":
    main()
