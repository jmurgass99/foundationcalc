"""Capacidad portante no drenada con carga excéntrica e inclinada (EN 1997-1 Anexo D.3) y N_γ según el autor (Anexo D, Brinch Hansen, Meyerhof, Vesić).

1) Zapata de 2,0 × 3,0 m a 1,2 m en arcilla (c_u = 60 kPa, γ = 19 kN/m³) con
   V = 900 kN, H = 80 kN y excentricidad e = 0,15 m a lo largo del lado largo.
   Anexo D.3: R/A' = (π + 2)·c_u·b_c·s_c·i_c + q, con s_c = 1 + 0,2·B'/L' e
   i_c = ½·(1 + √(1 − H/(A'·c_u))). Se calcula a mano y con
   `undrained_bearing_capacity`, y se barre H hasta H = A'·c_u (i_c = 0,5).
2) Factor N_γ: EN 1997-1 Anexo D da 2·(N_q − 1)·tan φ; Brinch Hansen
   1,5·(N_q − 1)·tan φ; Meyerhof (N_q − 1)·tan(1,4·φ); Vesić 2·(N_q + 1)·tan φ.
   Se tabula para φ = 25° a 40° y se comprueba cada fórmula a mano.

Ejecutar:  python examples/bearing_capacity_undrained_clay_inclined_eccentric_load_effective_area_and_ngamma_by_author.py
"""
import math

from foundationcalc import (
    BearingCapacityFormula, RectangularFoundation, SoilLayer, SoilType,
    bearing_capacity_factors, undrained_bearing_capacity,
)


def main() -> None:
    B, L, D, cu, gamma = 2.0, 3.0, 1.2, 60.0, 19.0
    V, H, e = 900.0, 80.0, 0.15
    fdn = RectangularFoundation(length=L * 1000, width=B * 1000, thickness=600, embedment_depth=D * 1000)
    clay = SoilLayer(name="arcilla", thickness=10, soil_type=SoilType.COHESIVE, friction_angle=0.0,
                     undrained_shear_strength=cu, unit_weight=gamma)

    Lp, Bp = L - 2 * e, B
    Ap = Lp * Bp
    sc = 1 + 0.2 * Bp / Lp
    ic = 0.5 * (1 + math.sqrt(1 - H / (Ap * cu)))
    q_hand = (math.pi + 2) * cu * sc * ic + gamma * D
    r = undrained_bearing_capacity(fdn, clay, e_x=e, H_load=H)
    print(f"Zapata {B} × {L} m, D = {D} m, c_u = {cu} kPa; V = {V:.0f} kN, H = {H:.0f} kN, e = {e} m")
    print(f"A mano: B' = {Bp:.2f} m, L' = {Lp:.2f} m, A' = {Ap:.2f} m², s_c = {sc:.4f}, i_c = {ic:.4f}; "
          f"q_ult = 5,1416·{cu:.0f}·{sc:.4f}·{ic:.4f} + {gamma * D:.1f} = {q_hand:.1f} kPa")
    print(f"Paquete: A' = {r.A_eff:.2f} m², s_c = {r.sc:.4f}, i_c = {r.ic:.4f}, q_ult = {r.q_ult:.1f} kPa "
          f"(diferencia {(r.q_ult / q_hand - 1) * 100:+.4f} %); R_k = {r.R_k:.0f} kN, V/R_k = {V / r.R_k:.3f}")
    for gRv in (1.0, 1.4):
        rr = undrained_bearing_capacity(fdn, clay, e_x=e, H_load=H, gamma_Rv=gRv, gamma_cu=1.0)
        print(f"  γ_R;v = {gRv}: R_d = {rr.R_d:.0f} kN -> V/R_d = {V / rr.R_d:.3f} "
              f"({'cumple' if V <= rr.R_d else 'no cumple'})")

    print("\nBarrido de la carga horizontal (misma V y e):")
    print(f"  {'H [kN]':>7} {'H/(A·c_u)':>10} {'i_c':>6} {'q_ult [kPa]':>11}")
    for Hx in (0.0, 80.0, 160.0, 240.0, 324.0):
        rx = undrained_bearing_capacity(fdn, clay, e_x=e, H_load=Hx)
        print(f"  {Hx:7.0f} {Hx / (Ap * cu):10.3f} {rx.ic:6.3f} {rx.q_ult:11.1f}")
    print("  Con H = A'·c_u el deslizamiento no drenado se agota e i_c llega a 0,5: a partir de ahí gobierna el deslizamiento.")

    print("\nN_γ según el autor (N_q común = e^(π·tan φ)·tan²(45° + φ/2)):")
    print(f"  {'φ [°]':>5} {'N_q':>7} {'EN1997 D':>9} {'Hansen':>8} {'Meyerhof':>9} {'Vesić':>7}   máx. dif. a mano")
    for phi in (25.0, 30.0, 35.0, 40.0):
        t = math.tan(math.radians(phi))
        Nq = math.exp(math.pi * t) * math.tan(math.radians(45 + phi / 2)) ** 2
        hand = {
            BearingCapacityFormula.CHEN_EC7: 2 * (Nq - 1) * t,
            BearingCapacityFormula.BRINCH_HANSEN: 1.5 * (Nq - 1) * t,
            BearingCapacityFormula.MEYERHOF: (Nq - 1) * math.tan(math.radians(1.4 * phi)),
            BearingCapacityFormula.VESIC: 2 * (Nq + 1) * t,
        }
        pkg = {f: bearing_capacity_factors(phi, f)[2] for f in hand}
        dif = max(abs(pkg[f] / hand[f] - 1) for f in hand)
        print(f"  {phi:5.0f} {Nq:7.2f} {pkg[BearingCapacityFormula.CHEN_EC7]:9.2f} "
              f"{pkg[BearingCapacityFormula.BRINCH_HANSEN]:8.2f} {pkg[BearingCapacityFormula.MEYERHOF]:9.2f} "
              f"{pkg[BearingCapacityFormula.VESIC]:7.2f}   {dif:.1e}")
    p35 = {f: bearing_capacity_factors(35.0, f)[2] for f in BearingCapacityFormula}
    lo, hi = min(p35, key=p35.get), max(p35, key=p35.get)
    print(f"  A 35° el mayor N_γ es el de {hi.value} y el menor el de {lo.value} "
          f"({p35[hi] / p35[lo]:.2f} veces): el término de peso propio depende mucho del autor elegido.")


if __name__ == "__main__":
    main()
