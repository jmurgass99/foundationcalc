"""Deslizamiento y vuelco de una zapata (EN 1997-1 §6.5.3) y modo de rotura de Vesić por índice de rigidez.

1) Deslizamiento drenado: H_Rd = V_d·tan δ_d / γ_R;h con δ_d = φ'_d para
   hormigón in situ y δ_d = 2/3·φ'_d para prefabricado liso (§6.5.3(10)).
   N = 1200 kN, H = 300 kN, A' = 6 m², φ'k = 30°, en DA1-C1, DA1-C2 y DA2.
   Antes de la 1.1.0 el factor 2/3 se aplicaba a la tangente.
2) Deslizamiento no drenado: H_Rd = c_u,d·A'/γ_R;h con c_u = 40 kPa.
3) Vuelco: e_B = B/2 − (M_stb − M_dst)/V y tercio central.
4) Vesić (1973): I_r = G/(c' + q'·tan φ'), I_rc = ½·exp(2,85·cot(45° − φ'/2));
   con I_r < I_rc se reducen N_q y N_γ con ζ_q. Se calcula I_r a mano.

Ejecutar:  python examples/sliding_overturning_cast_in_situ_vs_precast_two_thirds_phi_undrained_and_vesic_failure_mode.py
"""
import math

from foundationcalc import (
    DesignApproach, LimitState, SoilLayer, SoilType, get_partial_factors, overturning_check,
    sliding_resistance_drained, sliding_resistance_undrained,
)
from foundationcalc.analysis.failure_mode import classify_failure_mode, critical_rigidity_index


def main() -> None:
    N, H, A, phi = 1200.0, 300.0, 6.0, 30.0
    sand = SoilLayer(name="arena", thickness=10, soil_type=SoilType.COHESIONLESS, friction_angle=phi, unit_weight=19.0)
    print(f"Deslizamiento drenado: N = {N:.0f} kN, H_d = {H:.0f} kN, A' = {A} m², φ'k = {phi}°")
    print(f"  {'Enfoque':<7} {'base':<13} {'γφ':>5} {'γRh':>5} {'δ_d [°]':>8} {'H_Rd [kN]':>9} {'a mano':>8} {'H_d/H_Rd':>8}")
    worst = None
    for da in (DesignApproach.DA1_C1, DesignApproach.DA1_C2, DesignApproach.DA2):
        pf = get_partial_factors(da, LimitState.GEO)
        for base, k in (("in situ", 1.0), ("prefabricada", 2 / 3)):
            r = sliding_resistance_drained(N_Ed=N, soil=sand, A_eff=A, H_Ed=H, delta_factor=k,
                                           gamma_phi=pf.soil.gamma_phi, gamma_Rh=pf.resistance.gamma_Rh)
            phid = math.atan(math.tan(math.radians(phi)) / pf.soil.gamma_phi)
            hand = N * math.tan(k * phid) / pf.resistance.gamma_Rh
            print(f"  {da.value:<7} {base:<13} {pf.soil.gamma_phi:5.2f} {pf.resistance.gamma_Rh:5.2f} {r.delta_d_deg:8.2f} "
                  f"{r.H_Rd:9.1f} {hand:8.1f} {r.utilization:8.3f}")
            if worst is None or r.utilization > worst[0]:
                worst = (r.utilization, da.value, base)
    print(f"  Gobierna {worst[1]} con base {worst[2]}: H_d/H_Rd = {worst[0]:.3f} "
          f"({'cumple' if worst[0] <= 1 else 'no cumple: hace falta llave de cortante o más axil'}).")
    old = math.degrees(math.atan(2 / 3 * math.tan(math.radians(phi))))
    print(f"  Con 2/3 sobre la tangente (antes de la 1.1.0) δ_d habría sido {old:.2f}° en vez de {2 / 3 * phi:.2f}° "
          f"(+{(math.tan(math.radians(old)) / math.tan(math.radians(2 / 3 * phi)) - 1) * 100:.1f} % de resistencia).")

    clay = SoilLayer(name="arcilla", thickness=10, soil_type=SoilType.COHESIVE, friction_angle=0.0,
                     undrained_shear_strength=40.0, unit_weight=19.0)
    for da in (DesignApproach.DA1_C2, DesignApproach.DA2):
        pf = get_partial_factors(da, LimitState.GEO)
        ru = sliding_resistance_undrained(N_Ed=N, soil=clay, A_eff=A, H_Ed=H, gamma_cu=pf.soil.gamma_cu,
                                          gamma_Rh=pf.resistance.gamma_Rh)
        print(f"No drenado {da.value}: H_Rd = 40/{pf.soil.gamma_cu}·{A}/{pf.resistance.gamma_Rh} = {ru.H_Rd:.1f} kN, "
              f"H_d/H_Rd = {ru.utilization:.2f} ({'cumple' if ru.utilization <= 1 else 'no cumple'})")

    B, V, M = 2.5, 1200.0, 900.0
    ov = overturning_check(M_dst_d=M, M_stb_d=V * B / 2, V_d=V, B=B)
    print(f"\nVuelco: B = {B} m, V = {V:.0f} kN, M_dst = {M:.0f} kN·m: e_B = {B / 2:.2f} − ({V * B / 2:.0f} − {M:.0f})/{V:.0f} "
          f"= {ov.e_B:.3f} m; M_dst/M_stb = {ov.utilization:.3f}; tercio central (B/6 = {B / 6:.3f} m): "
          f"{'sí' if ov.middle_third else 'no, hay despegue'}")

    qp = 95.0
    print(f"\nModo de rotura de Vesić bajo una zapata de 2 × 2 m a 5 m en arena suelta (φ' = 30°, q' = {qp:.0f} kPa, ν = 0,3):")
    print(f"  {'E [MPa]':>7} {'G [kPa]':>8} {'I_r a mano':>10} {'I_r':>8} {'I_rc':>6} {'modo':<15} {'ζ_q':>6}")
    for E in (4.0, 8.0, 30.0):
        G = E * 1000 / (2 * 1.3)
        Ir_hand = G / (qp * math.tan(math.radians(30)))
        fm = classify_failure_mode(E_kPa=E * 1000, nu=0.3, c_prime_kPa=0.0, phi_deg=30.0, q_prime_kPa=qp,
                                   B_m=2.0, L_m=2.0, Nq=18.40)
        print(f"  {E:7.0f} {G:8.0f} {Ir_hand:10.1f} {fm.I_r:8.1f} {fm.I_rc:6.1f} {fm.mode.value:<15} {fm.zeta_q:6.3f}")
    print(f"  I_rc(30°) = ½·exp(2,85·cot 30°) = {0.5 * math.exp(2.85 / math.tan(math.radians(30))):.1f} "
          f"(paquete {critical_rigidity_index(30.0):.1f}). Con I_r < I_rc el diseño desde CPT multiplica q_ult por ζ_q. "
          "La constante 2,85 y ζ_q sin término de forma B/L son las del módulo; la dependencia de B/L de la "
          "formulación de Vesić no se ha contrastado aquí.")


if __name__ == "__main__":
    main()
