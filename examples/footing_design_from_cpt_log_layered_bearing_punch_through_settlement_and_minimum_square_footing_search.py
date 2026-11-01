"""Zapata cuadrada diseñada desde un CPT: perfil derivado, portante estratificada, asiento y búsqueda del lado mínimo (con su supuesto de monotonía).

Perfil: 0–3,9 m arena densa (q_c = 12 MPa), 3,9–7,6 m arcilla blanda
(q_c = 0,9 MPa) y arena densa hasta 15 m; freático a 2 m. Zapata a D = 1,0 m
con N = 1500 kN, DA2.

Cadena del paquete (`design_footing_from_cpt`): estratificación del CPT en 4
bandas, parámetros por correlación, portante del estrato de apoyo y
punzonamiento a través de él hacia la arcilla (`multi_layer_bearing_capacity`),
reducción de Vesić, asiento bajo el centro (Boussinesq + elástico en arena +
consolidación en arcilla, hasta 2B bajo la base) y veredicto con q_Rd y un
asiento admisible de 75 mm.

`optimize_footing_dimensions` busca el lado mínimo por bisección, lo que supone
que «cumple» es monótono con B. Aquí no lo es: la profundidad de influencia
2B hace que las zapatas pequeñas apenas «vean» la arcilla. El ejemplo lo pone
de manifiesto comparando la bisección con un barrido completo.

Ejecutar:  python examples/footing_design_from_cpt_log_layered_bearing_punch_through_settlement_and_minimum_square_footing_search.py
"""
from foundationcalc import RectangularFoundation
from foundationcalc.analysis.cpt import CPTProfile, CPTReading
from foundationcalc.analysis.cpt_to_design import design_footing_from_cpt, soil_profile_from_cpt
from foundationcalc.analysis.reverse_design import optimize_footing_dimensions

D, N, S_LIM = 1.0, 1500.0, 75.0


def build_log() -> CPTProfile:
    rows = []
    for i in range(1, 76):
        z = round(0.2 * i, 2)
        if z <= 3.9:
            qc, fs, u2 = 12.0, 70.0, 0.0
        elif z <= 7.6:
            qc, fs, u2 = 0.9, 18.0, 9.81 * max(z - 2.0, 0) + 60.0
        else:
            qc, fs, u2 = 18.0, 110.0, 9.81 * (z - 2.0)
        rows.append(CPTReading(depth=z, q_c_MPa=qc, f_s_kPa=fs, u_2_kPa=u2))
    return CPTProfile(readings=rows, water_table_depth_m=2.0, gamma_above_wt_kN_m3=18.0, gamma_below_wt_kN_m3=19.0)


def run(cpt, B):
    fdn = RectangularFoundation(length=B * 1000, width=B * 1000, thickness=600, embedment_depth=D * 1000)
    return design_footing_from_cpt(cpt, fdn, founding_depth_m=D, q_applied_kPa=N / B ** 2, n_strata=4,
                                   settlement_limit_mm=S_LIM)


def main() -> None:
    cpt = build_log()
    prof = soil_profile_from_cpt(cpt, n_layers=4)
    z = 0.0
    print("Perfil derivado del CPT (4 bandas):")
    for layer in prof.layers:
        extra = (f"φ' = {layer.friction_angle:.1f}°" if layer.soil_type.value == "cohesionless"
                 else f"c_u = {layer.undrained_shear_strength:.1f} kPa")
        print(f"  {z:5.2f}–{z + layer.thickness:5.2f} m  {layer.soil_type.value:<12} {extra:<16} E = {layer.youngs_modulus:5.1f} MPa")
        z += layer.thickness

    print(f"\nZapata cuadrada a D = {D} m, N = {N:.0f} kN, DA2, asiento admisible {S_LIM:.0f} mm")
    print(f"{'B [m]':>5} {'q_Ed':>6} {'q_ult':>6} {'q_Rd':>6} {'util.':>6} {'s_inm':>6} {'s_cons':>7} {'veredicto':<10}")
    sweep = []
    B = 1.5
    while B <= 6.0 + 1e-9:
        r = run(cpt, B)
        ok = r.bearing_ok and r.settlement_ok
        sweep.append((B, ok))
        print(f"{B:5.2f} {N / B ** 2:6.1f} {r.bearing.q_ult_kPa:6.0f} {r.q_Rd_kPa:6.0f} {r.bearing_utilization:6.2f} "
              f"{r.settlement.s_immediate_mm:6.1f} {r.settlement.s_consolidation_mm:7.1f} {'cumple' if ok else 'no cumple':<10}")
        B += 0.5

    r = run(cpt, 2.5)
    print(f"\nCon B = 2,5 m gobierna «{r.bearing.governing_case}»: q_ult del estrato de apoyo "
          f"{r.bearing.bottom_strong_q_ult:.0f} kPa, de la arcilla sola {r.bearing.weak_layer_q_ult:.0f} kPa y con "
          f"punzonamiento a través de la arena {r.bearing.punching_q_ult:.0f} kPa; q_Rd = {r.bearing.q_ult_kPa:.0f}·"
          f"{r.failure_mode.zeta_q:.2f}/1,4 = {r.q_Rd_kPa:.0f} kPa.")

    opt = optimize_footing_dimensions(cpt, load_kN=N, founding_depth_m=D, settlement_limit_mm=S_LIM,
                                      B_min_mm=1500.0, B_max_mm=6000.0, tolerance_mm=25.0)
    first_ok = next((b for b, ok in sweep if ok), None)
    print(f"\nBisección del optimizador ({len(opt.history)} evaluaciones): B = {opt.best.B:.3f} m "
          f"(asiento {opt.best.settlement_mm:.1f} mm).")
    print(f"Barrido completo: el primer lado que cumple es B = {first_ok:.2f} m.")
    fails_after_pass = [b for i, (b, ok) in enumerate(sweep) if not ok and any(o for _, o in sweep[:i])]
    if fails_after_pass:
        print(f"  El veredicto NO es monótono con B: fallan {fails_after_pass} m aunque lados menores cumplen (el asiento "
              "de consolidación crece mientras la zona de influencia 2B entra en la arcilla y luego baja con q).")
    if first_ok is not None and opt.best.B > first_ok + 0.05:
        print("  La bisección, que supone monotonía, no ha encontrado el mínimo.")
    else:
        h1 = opt.history[1]
        print(f"  Aquí la bisección acierta: su primer punto medio (B = {h1.B:.2f} m) "
              f"{'cumplía' if h1.passes else 'fallaba'} y desde ahí solo exploró lados menores. Con otros límites "
              "de búsqueda podría caer en la zona que falla y converger a otro lado: revisa siempre el barrido.")
    print("Límites: la consolidación usa Cc = 0,30, e0 = 0,8, Cr = 0,05 y cv = 2 m²/año FIJOS (el CPT no los da) y el t90 "
          "se calcula con el espesor de cada subcapa de 0,5 m; el asiento se corta a 2B; el punzonamiento entre "
          "estratos es una heurística con K_s = tan φ, no el ábaco de Meyerhof-Hanna; el optimizador no comprueba el canto.")


if __name__ == "__main__":
    main()
