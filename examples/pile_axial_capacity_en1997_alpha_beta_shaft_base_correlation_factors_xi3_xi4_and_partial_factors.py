"""Capacidad axial de un pilote perforado por el método de cálculo de EN 1997-1 §7.6.2.3: fuste α/β, punta, factores ξ y coeficientes parciales.

Pilote de Ø800 mm y 18 m: arcilla de 0 a 8 m (c_u = 50 kPa, γ = 18 kN/m³) y
arena de 8 a 25 m (φ' = 34°, γ = 19 kN/m³), sin freático.
- Fuste en arcilla, método α: q_s = α·c_u con α = 0,5.
- Fuste en arena, método β: q_s = β·σ'v,medio con β = 0,35.
- Punta en arena: q_b = N_q·σ'v con el N_q de Prandtl-Reissner que el módulo
  toma por defecto (el de cimentación superficial; conservador para pilotes).
- R_c;k = min{R_cal/ξ3 ; R_cal/ξ4} (ec. 7.8): con un solo perfil, R_cal dividido
  por el MAYOR de los dos ξ. Antes de la 1.1.0 se dividía por el menor.
- R_c;d = R_b;k/γ_b + R_s;k/γ_s.
Todo se recalcula a mano.

Ejecutar:  python examples/pile_axial_capacity_en1997_alpha_beta_shaft_base_correlation_factors_xi3_xi4_and_partial_factors.py
"""
import math

from foundationcalc import Pile, SoilLayer, SoilProfile, SoilType, pile_axial_capacity


def main() -> None:
    clay = SoilLayer(name="arcilla", thickness=8.0, soil_type=SoilType.COHESIVE, friction_angle=0.0,
                     undrained_shear_strength=50.0, unit_weight=18.0)
    sand = SoilLayer(name="arena", thickness=17.0, soil_type=SoilType.COHESIONLESS, friction_angle=34.0, unit_weight=19.0)
    prof = SoilProfile(layers=[clay, sand])
    D, L = 0.8, 18.0
    pile = Pile(diameter=D * 1000, length=L * 1000)
    per, A = math.pi * D, math.pi * D ** 2 / 4

    Rs_clay = per * 8.0 * 0.5 * 50.0
    sv_mid = 18.0 * 8 + 19.0 * 5.0
    Rs_sand = per * 10.0 * 0.35 * sv_mid
    t = math.tan(math.radians(34.0))
    Nq = math.exp(math.pi * t) * math.tan(math.radians(62.0)) ** 2
    sv_tip = 18.0 * 8 + 19.0 * 10
    Rb = A * Nq * sv_tip
    R_cal = Rs_clay + Rs_sand + Rb
    print(f"Pilote Ø{D * 1000:.0f} mm, L = {L} m; perímetro {per:.4f} m, área {A:.4f} m²")
    print(f"  Fuste arcilla: {per:.4f}·8·0,5·50 = {Rs_clay:.1f} kN")
    print(f"  Fuste arena:   {per:.4f}·10·0,35·σ'v(13 m) = {per:.4f}·10·0,35·{sv_mid:.0f} = {Rs_sand:.1f} kN")
    print(f"  Punta: N_q(34°) = {Nq:.2f}; σ'v(18 m) = {sv_tip:.0f} kPa; R_b = {A:.4f}·{Nq:.2f}·{sv_tip:.0f} = {Rb:.1f} kN")
    print(f"  R_cal = {R_cal:.1f} kN\n")

    ref = pile_axial_capacity(pile, prof, sand, alpha_shaft=0.5, beta_shaft=0.35, xi3=1.0, xi4=1.0)
    print(f"Paquete con ξ = 1: R_b = {ref.R_bk:.1f}, R_s = {ref.R_sk:.1f}, R_c = {ref.R_ck:.1f} kN "
          f"(diferencia {(ref.R_ck / R_cal - 1) * 100:+.4f} %)\n")

    print(f"{'perfiles':>8} {'ξ3':>5} {'ξ4':>5} {'R_c;k [kN]':>10} {'con min(ξ) (antes)':>18}")
    for n, x3, x4 in ((1, 1.40, 1.40), (2, 1.35, 1.27), (3, 1.33, 1.23), (5, 1.29, 1.15)):
        r = pile_axial_capacity(pile, prof, sand, alpha_shaft=0.5, beta_shaft=0.35, xi3=x3, xi4=x4)
        print(f"{n:8d} {x3:5.2f} {x4:5.2f} {r.R_ck:10.1f} {R_cal / min(x3, x4):18.1f}")
    print("  (pares ξ3/ξ4 de la Tabla A.10 recomendada tal como suelen citarse; sin contrastar aquí)\n")

    rows = []
    print(f"{'conjunto':<20} {'γ_b':>5} {'γ_s':>5} {'γ_t':>5} {'R_c;d [kN]':>10} {'a mano':>8}")
    for name, gb, gs, gt in (("R1 perforado", 1.25, 1.0, 1.0), ("R2 perforado", 1.1, 1.1, 1.0),
                             ("R4 perforado", 1.6, 1.3, 1.0), ("solo γ_t = 1,5", 1.0, 1.0, 1.5)):
        r = pile_axial_capacity(pile, prof, sand, alpha_shaft=0.5, beta_shaft=0.35, gamma_b=gb, gamma_s=gs, gamma_t=gt)
        Rk = R_cal / 1.40
        hand = Rk / gt if (gt != 1.0 and gb == 1.0 and gs == 1.0) else Rk * Rb / R_cal / gb + Rk * (1 - Rb / R_cal) / gs
        rows.append((r.R_cd, name))
        print(f"{name:<20} {gb:5.2f} {gs:5.2f} {gt:5.2f} {r.R_cd:10.1f} {hand:8.1f}")
    low = min(rows)
    print(f"La punta aporta el {Rb / R_cal * 100:.0f} % de R_cal; de los conjuntos probados el que más reduce es "
          f"«{low[1]}» (R_c;d = {low[0]:.0f} kN). Los valores de γ son los que suelen citarse para pilotes perforados "
          "(EN 1997-1 Tabla A.7), sin contrastar aquí.")
    print("Límites: N_q de punta de Prandtl-Reissner salvo que se pase otro; β = 0,3 por defecto si no se da; sin "
          "rozamiento negativo ni efecto de grupo; los γ_b/γ_s de la tabla anterior son los del ejemplo, no del paquete "
          "(sus conjuntos A/M/R de cimentación superficial no traen los de pilotes).")


if __name__ == "__main__":
    main()
