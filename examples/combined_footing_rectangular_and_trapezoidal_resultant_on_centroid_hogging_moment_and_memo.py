"""Zapata combinada de dos pilares: rectangular centrada en la resultante, trapezoidal junto al lindero y memoria.

`design_combined_footing` dimensiona para presión uniforme: el centroide de la
planta tiene que caer en la resultante de las dos cargas. `d` es la distancia
del lindero a la cara exterior del pilar 1; su eje queda a d + c/2.

Caso A (rectangular): P1 = 900 kN, P2 = 1300 kN, s = 5,0 m, d = 0,5 m,
pilares de 45 cm, q_adm = 200 kPa. Se comprueba a mano el largo, el ancho y el
máximo momento entre pilares (donde el cortante se anula).
Caso B (trapezoidal): pilar 1 en el lindero (d = 0) con P1 = 600 kN y
P2 = 1200 kN: el centroide del trapecio, L/3·(B1 + 2B2)/(B1 + B2), tiene que
coincidir con la resultante. Antes de la 1.1.0 caía c/2 corto.
Al final, la memoria de `memos.combined_footing` para el caso A.

Ejecutar:  python examples/combined_footing_rectangular_and_trapezoidal_resultant_on_centroid_hogging_moment_and_memo.py
"""
from foundationcalc.design.combined_footing import CombinedFootingInputs, design_combined_footing
from foundationcalc.memos.combined_footing import CombinedFootingFullInput, render_combined_footing_memo


def main() -> None:
    P1, P2, s, d, c, qa = 900.0, 1300.0, 5.0, 0.5, 0.45, 200.0
    r = design_combined_footing(CombinedFootingInputs(P1_kN=P1, P2_kN=P2, col_spacing_m=s,
                                                      column_1_to_property_line_m=d, column_size_m=c, q_allow_kPa=qa))
    R = P1 + P2
    xR = P2 * s / R
    x1 = d + c / 2
    L = 2 * (x1 + xR)
    Bw = R / qa / L
    print(f"Caso A: P1 = {P1:.0f}, P2 = {P2:.0f} kN, s = {s} m, d = {d} m, c = {c} m, q_adm = {qa:.0f} kPa")
    print(f"  a mano: x_R = {P2:.0f}·{s}/{R:.0f} = {xR:.4f} m desde el pilar 1; L = 2·({x1:.3f} + {xR:.4f}) = {L:.4f} m; "
          f"B = {R:.0f}/{qa:.0f}/{L:.4f} = {Bw:.4f} m")
    print(f"  paquete: forma {r.shape}, L = {r.L_m:.4f} m, B = {r.B_m:.4f} m, A = {r.A_provided_m2:.3f} m² "
          f"(requerida {r.A_required_m2:.3f})")
    w = R / L
    x0 = P1 / w
    M_hand = w * x0 ** 2 / 2 - P1 * (x0 - x1)
    x2 = x1 + s
    M2_hand = w * x2 ** 2 / 2 - P1 * s
    print(f"  Viga invertida: w = {R:.0f}/{L:.4f} = {w:.2f} kN/m hacia arriba, pilares hacia abajo.")
    print(f"  Entre pilares el cortante se anula en x = P1/w = {x0:.4f} m: M = w·x²/2 − P1·(x − {x1:.3f}) = {M_hand:.1f} kN·m "
          f"(tracción arriba); paquete M_neg = {r.M_neg_kNm:.1f} kN·m")
    print(f"  Bajo el pilar 2: M = w·{x2:.3f}²/2 − P1·{s} = {M2_hand:.1f} kN·m (tracción abajo); paquete M_pos = {r.M_pos_kNm:.1f} kN·m")
    print(f"  Armadura total en el ancho B = {r.B_m:.3f} m (d = 520 mm): superior {r.As_top_mm2:.0f} mm² para "
          f"{abs(r.M_neg_kNm):.0f} kN·m, inferior {r.As_bot_mm2:.0f} mm² para {r.M_pos_kNm:.0f} kN·m. "
          "Antes de la 1.1.0 el momento entre pilares no se recogía y la armadura superior salía de los "
          f"{M2_hand:.0f} kN·m de bajo el pilar. {r.note}\n")

    P1b, P2b, cb = 600.0, 1200.0, 0.40
    rb = design_combined_footing(CombinedFootingInputs(P1_kN=P1b, P2_kN=P2b, col_spacing_m=4.0,
                                                       column_1_to_property_line_m=0.0, column_size_m=cb, q_allow_kPa=qa))
    xc = rb.L_m / 3 * (rb.B1_m + 2 * rb.B2_m) / (rb.B1_m + rb.B2_m)
    target = cb / 2 + P2b * 4.0 / (P1b + P2b)
    print(f"Caso B: pilar 1 en el lindero, P1 = {P1b:.0f}, P2 = {P2b:.0f} kN, s = 4 m, c = {cb} m")
    print(f"  paquete: forma {rb.shape}, L = {rb.L_m:.2f} m, B1 = {rb.B1_m:.3f} m (lindero), B2 = {rb.B2_m:.3f} m, "
          f"A = {rb.A_provided_m2:.3f} m²")
    print(f"  centroide del trapecio = {xc:.4f} m; resultante desde el lindero = c/2 + x_R = {target:.4f} m "
          f"-> {'coinciden: presión uniforme' if abs(xc - target) < 1e-9 else 'no coinciden'}")
    print(f"  con la fórmula anterior (sin c/2) el centroide habría ido a {target - cb / 2:.4f} m, "
          f"{cb / 2 * 100:.0f} cm corto.\n")

    memo = render_combined_footing_memo(CombinedFootingFullInput(
        P1_kN=P1, P2_kN=P2, distance_cols_m=s, L_m=round(r.L_m, 2), B_m=round(r.B_m, 2), h_m=0.8,
        col1_dim_m=c, col2_dim_m=c, q_adm_kPa=qa, c_kPa=0.0, phi_deg=32.0, D_f_m=1.2))
    print(f"Memoria (memos.combined_footing) con la planta del caso A redondeada y pilares centrados en la planta:")
    print(f"  σ_max = {memo.sigma_max_kPa:.1f} kPa, σ_min = {memo.sigma_min_kPa:.1f} kPa (e = {memo.e_m:.3f} m); "
          f"R_d = {memo.R_d_kN:.0f} kN frente a {R:.0f} kN -> {'cumple' if memo.is_safe_bearing else 'no cumple'}")
    print(f"  punzonamiento simplificado: v_Ed = {memo.v_Ed_col2_kPa:.0f} kPa frente a 0,33·√f'c = {memo.v_Rd_kPa:.0f} kPa")
    print("Límites: el diagrama de flectores usa la presión media aunque la planta sea trapezoidal; la memoria supone "
          "voladizos iguales (no el lindero) y su punzonamiento no descuenta la reacción del terreno ni lleva φ.")


if __name__ == "__main__":
    main()
