"""Muro de gravedad (hormigón en masa frente a gaviones) con empuje de Coulomb y φ de cálculo, y alzado de un muro de contrafuertes como losa continua.

1) Muro de gravedad trapecial sin zapata: H = 4,0 m, coronación 0,6 m, base
   2,6 m, trasdós vertical; relleno φ' = 32°, γ = 19 kN/m³, sobrecarga 10 kPa;
   apoyo en grava densa φ' = 36°, γ = 20 kN/m³. `GravityWallDesigner`:
   - peso propio con el centroide del trapecio x = [s² − (s − a)²/3]/(a + s);
   - empuje de Coulomb en el trasdós con δ_w = ⅔·φ_d (hormigón) o φ_d
     (gavión) y φ_d = atan(tan φ_k/γ_φ) del juego M del enfoque;
   - tierras con γ_G y sobrecarga con γ_Q (EN 1990, Tabla A1.2);
   - deslizamiento con δ_b = ⅔·φ_d (hormigón) o φ_d (gavión), núcleo
     central, portante de Hansen sin término de sobrecarga.
   Hasta la 1.1.0 el empuje usaba φ_k en todos los enfoques (DA1-C2 y DA3 no
   mayoraban el empuje) y la sobrecarga iba con γ_G. Se barre además el ancho
   de base hasta encontrar el mínimo que cumple en cada enfoque.
2) Muro de contrafuertes H = 8 m (alzado 0,35 m, contrafuertes cada 3 m):
   estabilidad global por el muro en ménsula equivalente y el alzado como
   losa continua horizontal: M_apoyo = p·L²/12, M_vano = p·L²/24 con
   p = γ_G·K_a·γ·H + γ_Q·K_a·q en la base del alzado.

Ejecutar:  python examples/gravity_wall_mass_concrete_vs_gabion_coulomb_design_phi_and_counterfort_stem_slab_moments_hand_check.py
"""
import math

from foundationcalc import Concrete, DesignApproach, LimitState, SoilLayer, SoilType, get_partial_factors
from foundationcalc.analysis.earth_pressure import Ka_coulomb
from foundationcalc.design.counterfort_wall import CounterfortWallDesigner, CounterfortWallGeometry
from foundationcalc.design.gravity_wall import (
    GravityWallDesigner, GravityWallGeometry, GravityWallLoading, GravityWallMaterial,
)
from foundationcalc.design.retaining_wall import RetainingWallLoading

APPROACHES = (DesignApproach.DA1_C1, DesignApproach.DA1_C2, DesignApproach.DA2, DesignApproach.DA3)


def phi_d(phi_k: float, gamma_phi: float) -> float:
    return math.degrees(math.atan(math.tan(math.radians(phi_k)) / gamma_phi))


def main() -> None:
    back = SoilLayer(name="relleno", thickness=10, soil_type=SoilType.COHESIONLESS, friction_angle=32.0, unit_weight=19.0)
    found = SoilLayer(name="apoyo", thickness=10, soil_type=SoilType.COHESIONLESS, friction_angle=36.0, unit_weight=20.0)
    a, s = 0.6, 2.6
    geo = GravityWallGeometry(H=4.0, top_width=a, stem_bottom=s)
    load = GravityWallLoading(backfill=back, foundation_soil=found, surcharge_q=10.0)

    print(f"Muro de gravedad H = 4,0 m, coronación {a} m, base {s} m (B/H = {s / 4:.2f}), q = 10 kPa")
    print(f"{'material':<14} {'enfoque':<7} {'W [kN/m]':>8} {'K_a,d':>6} {'H_d':>6} {'V_d':>6} {'e [m]':>6} "
          f"{'núcleo':>6} {'portante':>8} {'desliz.':>7} {'vuelco':>6}")
    worst = {}
    for mat in (GravityWallMaterial.MASS_CONCRETE, GravityWallMaterial.GABION):
        for da in APPROACHES:
            r = GravityWallDesigner(geo, load, material=mat, design_approach=da).check()
            u = max(r.bearing_utilization, r.sliding_utilization, r.overturning_utilization)
            if mat not in worst or u > worst[mat][0]:
                worst[mat] = (u, da.value)
            print(f"{mat.value:<14} {da.value:<7} {r.W_kN_per_m:8.1f} {r.K_a:6.4f} {r.H_d:6.1f} {r.V_d:6.1f} "
                  f"{r.e_x:6.3f} {'sí' if r.middle_third else 'no':>6} {r.bearing_utilization:8.3f} "
                  f"{r.sliding_utilization:7.3f} {r.overturning_utilization:6.3f}")
    for mat, (u, da) in worst.items():
        verdict = "cumple en los cuatro enfoques" if u <= 1 else "NO cumple en algún enfoque"
        print(f"  {mat.value}: peor relación {u:.3f} en {da} -> {verdict}")

    print("\nAncho de base mínimo (pasos de 5 cm) para que portante, deslizamiento y vuelco cumplan:")
    for mat in (GravityWallMaterial.MASS_CONCRETE, GravityWallMaterial.GABION):
        cells = []
        for da in APPROACHES:
            found_b = None
            for i in range(0, 61):
                b = 2.0 + 0.05 * i
                r = GravityWallDesigner(GravityWallGeometry(H=4.0, top_width=a, stem_bottom=b), load,
                                        material=mat, design_approach=da).check()
                if max(r.bearing_utilization, r.sliding_utilization, r.overturning_utilization) <= 1.0:
                    found_b = b
                    break
            cells.append(f"{da.value} {found_b:.2f} m (B/H {found_b / 4:.2f})" if found_b else f"{da.value} > 5,0 m")
        print(f"  {mat.value:<14} " + "; ".join(cells))
    print("  En DA3 el módulo aplica A1 (γ_G = 1,35) al empuje junto con M2; EN 1997-1 usa A2 para las acciones "
          "geotécnicas en DA3, así que esa columna queda del lado conservador.")

    # --- Comprobación a mano (hormigón en masa, DA2 y DA1-C2) ----------------
    W = 0.5 * (a + s) * 4.0 * 24.0
    x_W = (s ** 2 - (s - a) ** 2 / 3.0) / (a + s)
    r2 = GravityWallDesigner(geo, load, design_approach=DesignApproach.DA2).check()
    print(f"\nA mano: W = ½·({a} + {s})·4·24 = {W:.1f} kN/m (paquete {r2.W_kN_per_m:.1f}); "
          f"x_W = [s² − (s − a)²/3]/(a + s) = {x_W:.4f} m desde la puntera (paquete {r2.x_W_m:.4f})")
    for da in (DesignApproach.DA2, DesignApproach.DA1_C2):
        pf = get_partial_factors(da, LimitState.GEO)
        pd = phi_d(32.0, pf.soil.gamma_phi)
        K = Ka_coulomb(pd, 2.0 / 3.0 * pd, 90.0, 0.0)
        c = math.cos(math.radians(2.0 / 3.0 * pd))
        Hd = pf.actions.gamma_G_unfav * 0.5 * K * 19 * 16 * c + pf.actions.gamma_Q_unfav * K * 10 * 4 * c
        r = GravityWallDesigner(geo, load, design_approach=da).check()
        print(f"  {da.value}: φ_d = {pd:.2f}°, K_a(Coulomb, δ = ⅔φ_d) = {K:.4f}; "
              f"H_d = {pf.actions.gamma_G_unfav}·½·K·19·4²·cos δ + {pf.actions.gamma_Q_unfav}·K·10·4·cos δ = {Hd:.1f} kN/m "
              f"(paquete {r.H_d:.1f})")
    K_k = Ka_coulomb(32.0, 2.0 / 3.0 * 32.0, 90.0, 0.0)
    K_d = Ka_coulomb(phi_d(32.0, 1.25), 2.0 / 3.0 * phi_d(32.0, 1.25), 90.0, 0.0)
    print(f"  Con φ_k (antes de la 1.1.0) DA1-C2 tomaba K_a = {K_k:.4f}: {(1 - K_k / K_d) * 100:.0f} % menos empuje que con φ_d.")

    # --- Muro de contrafuertes -----------------------------------------------
    bf = SoilLayer(name="relleno", thickness=12, soil_type=SoilType.COHESIONLESS, friction_angle=30.0, unit_weight=19.0)
    fd = SoilLayer(name="apoyo", thickness=12, soil_type=SoilType.COHESIONLESS, friction_angle=34.0, unit_weight=20.0)
    cgeo = CounterfortWallGeometry(H=8.0, stem_thickness=0.35, toe=1.5, heel=4.5, base_thickness=0.8,
                                   counterfort_spacing_m=3.0, counterfort_thickness_m=0.40)
    cload = RetainingWallLoading(backfill=bf, foundation_soil=fd, surcharge_q=10.0)
    print("\nMuro de contrafuertes H = 8 m, alzado 0,35 m, contrafuertes de 0,40 m cada 3,0 m, puntera 1,5 m, talón 4,5 m:")
    print(f"  {'enfoque':<7} {'portante':>8} {'desliz.':>7} {'vuelco':>6} {'p_base':>7} {'M_apoyo':>8} {'M_vano':>7} {'M_contraf.':>10}")
    for da in APPROACHES:
        r = CounterfortWallDesigner(cgeo, cload, Concrete(fck=30), design_approach=da).check()
        g = r.global_check
        p = r.stem_M_support_kNm_per_m * 12.0 / 9.0
        print(f"  {da.value:<7} {g.bearing_utilization:8.3f} {g.sliding_utilization:7.3f} {g.overturning_utilization:6.3f} "
              f"{p:7.1f} {r.stem_M_support_kNm_per_m:8.1f} {r.stem_M_midspan_kNm_per_m:7.1f} {r.counterfort_M_base_kNm:10.0f}")
    pf = get_partial_factors(DesignApproach.DA2, LimitState.STR)
    K = Ka_coulomb(30.0, 20.0, 90.0, 0.0)
    p = pf.actions.gamma_G_unfav * K * 19 * 8 + pf.actions.gamma_Q_unfav * K * 10
    r = CounterfortWallDesigner(cgeo, cload, Concrete(fck=30), design_approach=DesignApproach.DA2).check()
    print(f"  A mano (DA2): K_a(Coulomb, δ = 20°) = {K:.4f}; p = 1,35·K·19·8 + 1,5·K·10 = {p:.1f} kPa; "
          f"M_apoyo = p·3²/12 = {p * 9 / 12:.1f} (paquete {r.stem_M_support_kNm_per_m:.1f}), "
          f"M_vano = p·3²/24 = {p * 9 / 24:.1f} kN·m/m (paquete {r.stem_M_midspan_kNm_per_m:.1f})")
    print(f"  El tirante del contrafuerte (T = P_h·tan δ = {r.counterfort_tie_T_kN:.0f} kN) es una regla del módulo, "
          "no un modelo de bielas: dimensiona el tirante talón-alzado con un modelo propio.")
    print("Límites: vuelco con coeficientes GEO (no el juego EQU); en el muro de gravedad, agua con la presión "
          "hidrostática completa además del empuje con γ total, sin término de sobrecarga en la portante; el alzado "
          "toma la presión de la base como uniforme en toda la losa (del lado seguro).")


if __name__ == "__main__":
    main()
