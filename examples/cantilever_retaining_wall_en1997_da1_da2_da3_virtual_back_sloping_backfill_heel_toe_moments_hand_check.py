"""Muro en ménsula según EN 1997-1: trasdós virtual con relleno horizontal e inclinado, cuatro enfoques y esfuerzos en talón y puntera.

Muro de 5,0 m de alzado (30/45 cm), puntera 1,0 m, talón 2,5 m, zapata de
0,55 m, relleno granular φ' = 33°, γ = 19 kN/m³, sobrecarga 10 kPa; terreno
de apoyo φ' = 32°, γ = 20 kN/m³. `CantileverWallDesigner`:
- empuje de Rankine en el trasdós virtual (vertical por el final del talón),
  paralelo al talud: K_a de Rankine con relleno inclinado y con el φ de cálculo
  del enfoque (M2 en DA1-C2 y DA3); tierras con γ_G y sobrecarga con γ_Q;
- deslizamiento con tan φ_d = tan φ/γ_φ, portante por ancho eficaz, vuelco
  EQU con coeficientes EQU sobre valores característicos;
- talón y puntera con la distribución real de presiones bajo la zapata.
Hasta la 1.1.0: el talud no cambiaba K_a, el empuje usaba φ_k en todos los
enfoques, la sobrecarga iba con γ_G, el ángulo (no la tangente) se dividía por
γ_φ en el deslizamiento, el vuelco EQU se mayoraba dos veces y la presión en
talón y puntera tenía signo y factor erróneos.

Ejecutar:  python examples/cantilever_retaining_wall_en1997_da1_da2_da3_virtual_back_sloping_backfill_heel_toe_moments_hand_check.py
"""
from foundationcalc import Concrete, DesignApproach, LimitState, SoilLayer, SoilType, get_partial_factors
from foundationcalc.analysis.earth_pressure import Ka_rankine_inclined
from foundationcalc.design.retaining_wall import CantileverWallDesigner, CantileverWallGeometry, RetainingWallLoading


def designer(slope, da):
    geo = CantileverWallGeometry(H=5.0, stem_top=0.30, stem_bottom=0.45, toe=1.0, heel=2.5, base_thickness=0.55,
                                 embedment_front=0.8)
    back = SoilLayer(name="relleno", thickness=10, soil_type=SoilType.COHESIONLESS, friction_angle=33.0, unit_weight=19.0)
    found = SoilLayer(name="apoyo", thickness=10, soil_type=SoilType.COHESIONLESS, friction_angle=32.0, unit_weight=20.0)
    load = RetainingWallLoading(backfill=back, foundation_soil=found, surcharge_q=10.0, backfill_slope_deg=slope)
    return CantileverWallDesigner(geo, load, Concrete(fck=30), design_approach=da)


def main() -> None:
    print(f"{'talud':>5} {'enfoque':<7} {'K_a,d':>6} {'H_d':>6} {'V_d':>6} {'e':>6} {'portante':>8} {'desliz.':>7} {'vuelco':>7} {'M_alzado':>8} {'M_talón':>7} {'M_punt.':>7}")
    worst = None
    for slope in (0.0, 15.0):
        for da in (DesignApproach.DA1_C1, DesignApproach.DA1_C2, DesignApproach.DA2, DesignApproach.DA3):
            d = designer(slope, da)
            r = d.check()
            pfd = get_partial_factors(da, LimitState.GEO)
            Ka = d._active_thrust_parts(pfd.soil.gamma_phi, pfd.soil.gamma_c)["K"]
            u = max(r.bearing_utilization, r.sliding_utilization, r.overturning_utilization)
            if worst is None or u > worst[0]:
                worst = (u, slope, da.value)
            print(f"{slope:5.0f} {da.value:<7} {Ka:6.4f} {r.actions.H_d:6.1f} {r.actions.V_d:6.1f} {r.actions.e_x:6.3f} "
                  f"{r.bearing_utilization:8.3f} {r.sliding_utilization:7.3f} {r.overturning_utilization:7.3f} "
                  f"{r.M_stem_base:8.1f} {r.M_heel:7.1f} {r.M_toe:7.1f}")
    print(f"Peor relación: {worst[0]:.3f} (talud {worst[1]:.0f}°, {worst[2]}) -> "
          f"{'el muro cumple en todos los casos' if worst[0] <= 1 else 'el muro no cumple en algún caso'}.")
    print("Gobierna DA3 porque el módulo combina A1 (γ_G = 1,35) con el φ de cálculo M2 sobre el empuje; EN 1997-1 "
          "aplica A2 a las acciones geotécnicas en DA3, así que este resultado queda del lado conservador.\n"
          if worst[2] == "DA3" else "\n")

    d = designer(0.0, DesignApproach.DA2)
    a = d._factored_actions()
    r = d.check()
    pf = get_partial_factors(DesignApproach.DA2, LimitState.GEO)
    Ka = Ka_rankine_inclined(33.0, 0.0)
    Hv = 5.55
    Hd = 1.35 * 0.5 * Ka * 19 * Hv ** 2 + 1.5 * Ka * 10 * Hv
    print(f"DA2 a mano: H_v = {Hv} m, K_a = {Ka:.4f}; H_d = 1,35·½·K_a·19·{Hv}² + 1,5·K_a·10·{Hv} = {Hd:.1f} kN/m "
          f"(paquete {a.H_d:.1f})")
    B, V, e = 3.95, a.V_d, a.e_x
    q = lambda x: V / B * (1 + 12 * e * (B / 2 - x) / B ** 2)  # noqa: E731
    gG = 1.35
    w_heel = gG * (25 * 0.55 + 19 * 5.0) + 1.5 * 10.0
    M_heel = w_heel * 2.5 ** 2 / 2 - 2.5 ** 2 * (q(1.45) + 2 * q(B)) / 6
    w_toe = gG * (25 * 0.55 + 19 * 0.8)
    M_toe = 1.0 ** 2 * (2 * q(0.0) + q(1.0)) / 6 - w_toe * 1.0 ** 2 / 2
    print(f"  presiones: q(puntera) = {q(0):.1f}, q(cara puntera) = {q(1.0):.1f}, q(cara talón) = {q(1.45):.1f}, "
          f"q(final talón) = {q(B):.1f} kPa (e = {e:.3f} m hacia la puntera)")
    print(f"  talón: M = {w_heel:.1f}·2,5²/2 − 2,5²·(q_a + 2q_b)/6 = {M_heel:.1f} kN·m/m (paquete {r.M_heel:.1f}); "
          f"puntera: M = (2q_0 + q_t)/6 − {w_toe:.1f}/2 = {M_toe:.1f} kN·m/m (paquete {r.M_toe:.1f})")
    tan_d = 0.6249 / pf.soil.gamma_phi
    print(f"  deslizamiento: H_Rd = V_d·tan 32°/γ_φ/γ_R;h = {V:.1f}·{tan_d:.4f}/{pf.resistance.gamma_Rh} = "
          f"{V * tan_d / pf.resistance.gamma_Rh:.1f} kN/m (paquete {r.sliding_H_Rd:.1f})")
    print("Límites: peso del relleno sobre el talón con superficie horizontal aunque haya talud; alzado con Coulomb sin "
          "componente cos δ; la portante sustituye el muro por una faja de 10 m; sin agua salvo `water_height`.")


if __name__ == "__main__":
    main()
