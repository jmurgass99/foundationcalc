"""Zapata de grúa torre: casos de servicio y de tormenta en DA1-C1, DA1-C2 y DA2, y barrido del lado mínimo que cumple.

Datos de fabricante habituales (en la base del mástil):
- en servicio: N = 700 kN, M = 2400 kN·m, V = 60 kN, coeficiente dinámico 1,10;
- fuera de servicio (tormenta): N = 500 kN, M = 3200 kN·m, V = 130 kN.
Arena con grava densa (φ'k = 36°, γ = 19 kN/m³), 1,5 m de relleno sobre la
zapata, hormigón de 25 kN/m³, canto 1,6 m, mástil de 2 × 2 m.

`crane_foundation_check` mayora (tormenta: γ_Q al momento; servicio: γ_G), suma
el peso propio y el relleno, calcula presiones con despegue
(`BasePressureAnalysis`), capacidad portante por área eficaz, deslizamiento y
vuelco. El ejemplo comprueba a mano la excentricidad y la presión del caso de
tormenta en DA2 y busca el menor lado (de 0,25 en 0,25 m) que cumple todo.

Ejecutar:  python examples/tower_crane_pad_in_service_and_storm_cases_four_design_approaches_minimum_side_sweep.py
"""
from foundationcalc import (
    Column, Concrete, CraneLoadCase, CraneLoadState, DesignApproach, RectangularFoundation,
    SoilLayer, SoilType, crane_foundation_check, get_partial_factors, LimitState,
)

SAND = SoilLayer(name="arena con grava", thickness=12.0, soil_type=SoilType.COHESIONLESS,
                 friction_angle=36.0, cohesion=0.0, unit_weight=19.0)
C30 = Concrete(name="C30/37", fck=30.0)
SERVICE = CraneLoadCase(state=CraneLoadState.SERVICE, name="servicio", N_kN=700.0, M_x_kNm=2400.0,
                        V_y_kN=60.0, is_wind_dominant=False, dynamic_factor=1.10)
STORM = CraneLoadCase(state=CraneLoadState.OUT_OF_SERVICE, name="tormenta", N_kN=500.0, M_x_kNm=3200.0,
                      V_y_kN=130.0, is_wind_dominant=True)
DAS = (DesignApproach.DA1_C1, DesignApproach.DA1_C2, DesignApproach.DA2)
T, H_FILL = 1.6, 1.5


def pad(side):
    f = RectangularFoundation(length=side * 1000, width=side * 1000, thickness=T * 1000, embedment_depth=H_FILL * 1000)
    m = Column(length=2000, width=2000, pos_x=side * 500, pos_y=side * 500)
    return f, m


def check(side, lc, da):
    f, m = pad(side)
    return crane_foundation_check(foundation=f, column=m, load_case=lc, soil=SAND, concrete=C30, design_approach=da,
                                  soil_overburden_depth_mm=H_FILL * 1000, soil_unit_weight_overburden=19.0)


def main() -> None:
    side = 6.5
    print(f"Zapata {side} × {side} × {T} m con {H_FILL} m de relleno; mástil 2 × 2 m\n")
    print(f"{'caso':<9} {'enfoque':<7} {'e [m]':>6} {'régimen':<14} {'q_max':>7} {'portante':>8} {'desliz.':>8} {'vuelco':>7}")
    for lc in (SERVICE, STORM):
        for da in DAS:
            r = check(side, lc, da)
            print(f"{lc.name:<9} {da.value:<7} {r.e_y:6.3f} {r.regime:<14} {r.q_max:7.1f} {r.bearing_utilization:8.3f} "
                  f"{r.sliding_utilization:8.3f} {r.overturning_utilization:7.3f}")

    pf = get_partial_factors(DesignApproach.DA2, LimitState.GEO)
    A = side ** 2
    W = A * (T * 25.0 + H_FILL * 19.0)
    N_d = pf.actions.gamma_G_unfav * (STORM.N_kN + W)
    M_d = pf.actions.gamma_Q_unfav * (STORM.M_x_kNm + STORM.V_y_kN * T)
    e = M_d / N_d
    q_hand = 2 * N_d / (3 * side * (side / 2 - e)) if e > side / 6 else N_d / A * (1 + 6 * e / side)
    r = check(side, STORM, DesignApproach.DA2)
    print(f"\nA mano, tormenta DA2: W = {A:.2f}·({T}·25 + {H_FILL}·19) = {W:.1f} kN; N_d = 1,35·({STORM.N_kN:.0f} + {W:.1f}) = {N_d:.1f} kN;")
    print(f"  M_d = 1,50·({STORM.M_x_kNm:.0f} + {STORM.V_y_kN:.0f}·{T}) = {M_d:.1f} kN·m; e = {e:.4f} m "
          f"({'fuera' if e > side / 6 else 'dentro'} del núcleo L/6 = {side / 6:.3f} m); q_max = {q_hand:.1f} kPa "
          f"(paquete e = {r.e_y:.4f} m, q_max = {r.q_max:.1f} kPa)")

    print("\nBarrido del lado (todos los enfoques y los dos casos):")
    found = None
    s = 4.5
    while s <= 6.5 + 1e-9:
        worst = max(((max(c.bearing_utilization, c.sliding_utilization, c.overturning_utilization), lc.name, da.value)
                     for lc in (SERVICE, STORM) for da in DAS for c in [check(s, lc, da)]))
        ok = worst[0] <= 1.0
        rel = f"{worst[0]:.3f}" if worst[0] < 1e3 else "∞ (área eficaz nula: resultante en el borde)"
        print(f"  lado {s:4.2f} m: peor relación {rel} ({worst[1]}, {worst[2]}) -> {'cumple' if ok else 'no cumple'}")
        if ok and found is None:
            found = s
        s += 0.25
    print(f"Lado mínimo que cumple todo: {found:.2f} m." if found else "Ningún lado del barrido cumple.")
    print("Límites: en servicio el momento del gancho se mayora con γ_G (criterio del módulo, no EN 1991-3); el vuelco se "
          "toma con el momento resultante sobre el lado menor y el canto no se comprueba estructuralmente.")


if __name__ == "__main__":
    main()
