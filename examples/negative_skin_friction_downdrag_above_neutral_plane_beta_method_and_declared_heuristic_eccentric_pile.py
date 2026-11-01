"""Rozamiento negativo sobre un pilote (método β por encima del plano neutro) y la comprobación heurística de pilote con carga excéntrica.

1) Pilote de Ø0,6 m que atraviesa 2 m de relleno (γ = 18 kN/m³, no consolida)
   y 8 m de arcilla blanda en consolidación (γ' = 8 kN/m³, β = 0,25) bajo un
   relleno nuevo; plano neutro a 8 m; carga permanente 900 kN.
   `downdrag`: Q_neg = Σ β·σ'v,medio·π·D·Δz en los estratos que consolidan,
   por encima del plano neutro. Se recalcula a mano y se barre la posición del
   plano neutro.
2) `pilote_excentrico.evaluar`: capacidad lateral y a momento con
   coeficientes «tipo Brinch Hansen» (K_q = (1 + tan φ)²·(1 + 0,5·z/D),
   K_c = 5·(1 + 0,2·z/D)) e interacción lineal. Es una heurística del módulo
   que no reproduce el método de Brinch Hansen (1961); se muestra para
   declararla, no para dimensionar.

Ejecutar:  python examples/negative_skin_friction_downdrag_above_neutral_plane_beta_method_and_declared_heuristic_eccentric_pile.py
"""
import math

from foundationcalc.analysis.friccion_negativa import FriccionNegativaInput, Layer, downdrag
from foundationcalc.analysis.pilote_excentrico import PiloteExcentricoInput, evaluar


def main() -> None:
    D = 0.6
    layers = (Layer(z_top_m=0.0, z_bot_m=2.0, gamma_kN_m3=18.0, beta=0.0, consolidando=False),
              Layer(z_top_m=2.0, z_bot_m=10.0, gamma_kN_m3=8.0, beta=0.25, consolidando=True))
    r = downdrag(FriccionNegativaInput(pile_diameter_m=D, layers=layers, z_neutro_m=8.0, Q_dead_kN=900.0))
    s_top, s_bot = 18.0 * 2, 18.0 * 2 + 8.0 * 6
    hand = 0.25 * (s_top + s_bot) / 2 * math.pi * D * 6
    print(f"Pilote Ø{D} m; relleno 0–2 m (no consolida), arcilla 2–10 m (β = 0,25), plano neutro a 8 m")
    print(f"  a mano: σ'v(2 m) = {s_top:.0f}, σ'v(8 m) = {s_bot:.0f} kPa; Q_neg = 0,25·{(s_top + s_bot) / 2:.0f}·π·{D}·6 = {hand:.1f} kN")
    print(f"  paquete: Q_neg = {r.Q_neg_kN:.1f} kN; carga de servicio en el plano neutro = 900 + {r.Q_neg_kN:.1f} = "
          f"{r.Q_total_servicio_kN:.1f} kN ({r.Q_neg_kN / 900 * 100:.0f} % más)")
    print("  Plano neutro:", ", ".join(
        f"{zn:.0f} m -> {downdrag(FriccionNegativaInput(pile_diameter_m=D, layers=layers, z_neutro_m=zn, Q_dead_kN=900.0)).Q_neg_kN:.0f} kN"
        for zn in (4.0, 6.0, 8.0, 10.0)))
    print("  El paquete no calcula la posición del plano neutro (equilibrio de fuste y punta frente a asientos): "
          "hay que darla.\n")

    print("Heurística de pilote con carga excéntrica (no es Brinch Hansen):")
    for H, M in ((50.0, 0.0), (50.0, 100.0), (120.0, 200.0)):
        e = evaluar(PiloteExcentricoInput(D_m=0.8, L_m=12.0, N_kN=900.0, H_kN=H, M_kNm=M, phi_deg=30.0, gamma_kN_m3=18.0))
        print(f"  H = {H:5.0f} kN, M = {M:5.0f} kN·m: H_adm = {e.H_admisible_kN:7.1f} kN, M_adm = {e.M_admisible_kNm:7.1f} kN·m, "
              f"H/H_adm + M/M_adm = {e.interaction_ratio:.3f} -> {'cumple' if e.cumple else 'no cumple'}")
    Kq = (1 + math.tan(math.radians(30))) ** 2 * (1 + 0.5 * 6.0 / 0.8)
    print(f"  K_q(z = L/2) = (1 + tan 30°)²·(1 + 0,5·6/0,8) = {Kq:.2f}; H_adm = 18·6·K_q·0,8·12/2 = {18 * 6 * Kq * 0.8 * 12 / 2:.0f} kN: "
          "la capacidad lateral sale de un empuje medio sobre medio fuste, sin mecanismo de rotura ni momento de "
          "plastificación del pilote. Para pilotes con carga lateral usa `solve_pile_lateral`.")


if __name__ == "__main__":
    main()
