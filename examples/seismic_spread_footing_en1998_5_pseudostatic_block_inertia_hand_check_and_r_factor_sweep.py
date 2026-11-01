"""Zapata aislada bajo sismo (EN 1998-5, pseudoestático): inercia del bloque, área eficaz, portante, deslizamiento y vuelco.

Zapata de 3,0 × 3,0 × 0,7 m a 1,2 m en arena (φ'k = 34°), pilar de un
edificio de 5 plantas en zona de sismicidad moderada (a_g = 0,20·g, suelo C,
S = 1,15). En la base del pilar, combinación sísmica: N = 990 kN
(G + ψ2·Q), H = 180 kN, M = 420 kN·m.

`seismic_footing_check` añade la inercia horizontal del bloque
(H_in = k_h·W, con k_h = a_g·γ_I·S/r) y su momento en la base (H_in·t/2), resta
el efecto de la aceleración vertical (k_v = 0,5·k_h) y comprueba con DA3.
El ejemplo reproduce N, M y la excentricidad a mano (antes de la 1.1.0 la
inercia del bloque entraba en la excentricidad con brazo 1,5·t) y barre el
factor r.

Ejecutar:  python examples/seismic_spread_footing_en1998_5_pseudostatic_block_inertia_hand_check_and_r_factor_sweep.py
"""
from foundationcalc import Column, Concrete, RectangularFoundation, SoilLayer, SoilType
from foundationcalc.analysis.seismic_footing import SeismicAction, seismic_footing_check


def main() -> None:
    B, t, D = 3.0, 0.7, 1.2
    N, H, M = 990.0, 180.0, 420.0
    fdn = RectangularFoundation(length=B * 1000, width=B * 1000, thickness=t * 1000, embedment_depth=D * 1000)
    col = Column(length=500, width=500, pos_x=B * 500, pos_y=B * 500)
    sand = SoilLayer(name="arena", thickness=10, soil_type=SoilType.COHESIONLESS, friction_angle=34.0, unit_weight=19.0)
    act = SeismicAction(a_g=0.20, S=1.15)
    r = seismic_footing_check(fdn, col, N, H, M, sand, Concrete(fck=30), act)

    W = B * B * t * 25.0
    kh = 0.20 * 1.0 * 1.15 / 1.0
    H_in = kh * W
    N_tot = N + W - 0.5 * kh * W
    M_tot = M + H * t + H_in * t / 2
    print(f"Zapata {B} × {B} × {t} m a {D} m; N = {N:.0f} kN, H = {H:.0f} kN, M = {M:.0f} kN·m; a_g = 0,20 g, S = 1,15, r = 1")
    print(f"A mano: W = {W:.1f} kN; k_h = {kh:.3f}; H_in = {H_in:.3f} kN; N_tot = {N:.0f} + {W:.1f} − 0,5·{kh:.3f}·{W:.1f} = {N_tot:.3f} kN")
    print(f"        M_tot = {M:.0f} + {H:.0f}·{t} + {H_in:.3f}·{t}/2 = {M_tot:.3f} kN·m; e = {M_tot / N_tot:.4f} m")
    print(f"Paquete: N_d = {r.N_d:.3f} kN, M_d = {r.M_d:.3f} kN·m, e_y = {r.e_y:.4f} m, régimen {r.regime}, q_max = {r.q_max:.1f} kPa\n")
    print(f"{'comprobación':<12} {'E_d':>9} {'R_d':>9} {'E_d/R_d':>8}")
    print(f"{'portante':<12} {r.bearing_q_Ed:9.1f} {r.bearing_q_Rd:9.1f} {r.bearing_utilization:8.3f}   (kPa, área eficaz)")
    print(f"{'deslizam.':<12} {r.sliding_H_Ed:9.1f} {r.sliding_H_Rd:9.1f} {r.sliding_utilization:8.3f}   (kN)")
    print(f"{'vuelco':<12} {r.overturning_M_dst:9.1f} {r.overturning_M_stb:9.1f} {r.overturning_utilization:8.3f}   (kN·m)")
    print(f"Veredicto: {'cumple' if r.all_ok else 'no cumple'}; resultante en el tercio central: {'sí' if r.middle_third else 'no'}.")
    import math
    phid = math.atan(math.tan(math.radians(34.0)) / 1.25)
    i_s = (1 - kh / math.tan(phid)) ** 3
    gov = max((r.bearing_utilization, "portante"), (r.sliding_utilization, "deslizamiento"),
              (r.overturning_utilization, "vuelco"))
    print(f"Gobierna {gov[1]}. Con DA3 φ_d = {math.degrees(phid):.2f}° y el factor sísmico del módulo "
          f"(1 − k_h/tan φ_d)³ = {i_s:.3f} multiplica toda la q_ult: es lo que más pesa en la portante.\n")

    print("Barrido del factor r de EN 1998-5 (k_h = a_g·S/r):")
    print(f"  {'r':>4} {'k_h':>6} {'portante':>9} {'desliz.':>8} {'vuelco':>7}")
    for rr in (1.0, 1.5, 2.0):
        res = seismic_footing_check(fdn, col, N, H, M, sand, Concrete(fck=30), SeismicAction(a_g=0.20, S=1.15, r_factor=rr))
        print(f"  {rr:4.1f} {0.23 / rr:6.3f} {res.bearing_utilization:9.3f} {res.sliding_utilization:8.3f} {res.overturning_utilization:7.3f}")
    print("Límites: la reducción sísmica de la portante es el factor (1 − k_h/tan φ_d)³ del módulo, no la superficie "
          "de rotura del Anexo F de EN 1998-5; el vuelco se toma sobre el lado menor con el momento total.")


if __name__ == "__main__":
    main()
