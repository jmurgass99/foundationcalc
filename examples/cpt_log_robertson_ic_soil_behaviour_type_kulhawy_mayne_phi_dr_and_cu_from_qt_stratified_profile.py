"""Interpretación de un ensayo CPTu: índice I_c de Robertson, tipo de comportamiento, φ' y D_R de Kulhawy y Mayne, c_u y estratificación.

Perfil costero mediterráneo sintético con nivel freático a 2 m:
- 0–3 m: arena de relleno (q_c ≈ 6 MPa, f_s ≈ 40 kPa);
- 3–7 m: arcilla blanda normalmente consolidada (q_c ≈ 0,9 MPa, f_s ≈ 18 kPa, u_2 alto);
- 7–15 m: arena densa (q_c ≈ 18 MPa, f_s ≈ 110 kPa).

Fórmulas (módulo `analysis.cpt`):
  q_t = q_c + (1 − a_n)·u_2;  Q_t = (q_t − σ_v0)/σ'_v0;  F_r = f_s/(q_t − σ_v0)·100
  I_c = √((3,47 − log Q_t)² + (log F_r + 1,22)²)  (Robertson 2009)
  φ' = 17,6 + 11·log Q_tn, D_R² = Q_tn/305  (Kulhawy y Mayne 1990), Q_tn = (q_t/p_a)/√(σ'_v0/p_a)
  c_u = (q_t − σ_v0)/N_kt con N_kt = 14
Se comprueba a mano una lectura de cada estrato.

Ejecutar:  python examples/cpt_log_robertson_ic_soil_behaviour_type_kulhawy_mayne_phi_dr_and_cu_from_qt_stratified_profile.py
"""
import math

from foundationcalc.analysis.cpt import (
    CPTProfile, CPTReading, cu_from_qt, phi_from_qt_kulhawy_mayne, relative_density_kulhawy_mayne,
)


def build_log() -> CPTProfile:
    rows = []
    z = 0.2
    while z <= 15.0 + 1e-9:
        if z <= 3.0:
            qc, fs, u2 = 6.0 + 0.3 * z, 40.0, 0.0
        elif z <= 7.0:
            qc, fs, u2 = 0.8 + 0.03 * (z - 3.0), 18.0, 9.81 * (z - 2.0) + 60.0
        else:
            qc, fs, u2 = 16.0 + 0.3 * (z - 7.0), 110.0, 9.81 * (z - 2.0)
        rows.append(CPTReading(depth=round(z, 2), q_c_MPa=qc, f_s_kPa=fs, u_2_kPa=u2, a_n=0.8))
        z += 0.2
    return CPTProfile(readings=rows, water_table_depth_m=2.0, gamma_above_wt_kN_m3=18.0, gamma_below_wt_kN_m3=19.0)


def main() -> None:
    cpt = build_log()
    print(f"CPTu de {len(cpt.readings)} lecturas cada 0,2 m, nivel freático a {cpt.water_table_depth_m} m\n")
    print(f"{'z [m]':>5} {'q_t [MPa]':>9} {'σv0':>6} " + f"{'σ_v0_eff':>6} {'Q_t':>6} {'F_r %':>6} {'I_c':>5} {'zona SBT':<18}")
    for zq in (1.0, 2.6, 4.0, 6.0, 8.0, 12.0):
        r = next(x for x in cpt.readings if abs(x.depth - zq) < 1e-6)
        print(f"{zq:5.1f} {r.q_t_MPa:9.3f} {cpt.total_stress_kPa(zq):6.1f} {cpt.effective_stress_kPa(zq):6.1f} "
              f"{cpt.Q_t(r):6.1f} {cpt.F_r_pct(r):6.2f} {cpt.i_c(r):5.2f} {cpt.sbt_zone(r).name:<18}")

    print("\nA mano en z = 4,0 m (arcilla) y z = 12,0 m (arena):")
    for zq in (4.0, 12.0):
        r = next(x for x in cpt.readings if abs(x.depth - zq) < 1e-6)
        sv = 18.0 * 2.0 + 19.0 * (zq - 2.0)
        u = 9.81 * (zq - 2.0)
        se = sv - u
        qt = r.q_c_MPa + 0.2 * r.u_2_kPa / 1000
        Qt = (qt * 1000 - sv) / se
        Fr = r.f_s_kPa / (qt * 1000 - sv) * 100
        Ic = math.sqrt((3.47 - math.log10(Qt)) ** 2 + (math.log10(Fr) + 1.22) ** 2)
        print(f"  z = {zq}: σv0 = 18·2 + 19·{zq - 2:.0f} = {sv:.1f} kPa, u = {u:.1f}, σ'v0 = {se:.1f}; q_t = {qt:.4f} MPa; "
              f"Q_t = {Qt:.2f}, F_r = {Fr:.2f} %, I_c = {Ic:.3f} (paquete {cpt.i_c(r):.3f})")
        if zq < 7:
            print(f"    c_u = ({qt * 1000:.1f} − {sv:.1f})/14 = {(qt * 1000 - sv) / 14:.1f} kPa "
                  f"(paquete {cu_from_qt(qt * 1000, sv):.1f})")
        else:
            Qtn = (qt / 0.1) / math.sqrt(se / 100)
            print(f"    Q_tn = {Qtn:.1f}: φ' = 17,6 + 11·log Q_tn = {17.6 + 11 * math.log10(Qtn):.1f}° "
                  f"(paquete {phi_from_qt_kulhawy_mayne(qt, se / 1000):.1f}°), D_R = √(Q_tn/305) = "
                  f"{math.sqrt(Qtn / 305) * 100:.0f} % (paquete {relative_density_kulhawy_mayne(qt, se / 1000):.0f} %)")

    print("\nEstratificación en 5 bandas iguales (`stratify`):")
    print(f"  {'z_top':>5} {'z_bot':>5} {'q_t medio':>9} {'I_c':>5} {'zona':<18} " + f"{'phi_eff [deg]':>15} {'c_u [kPa]':>9} {'E [MPa]':>8}")
    for s in cpt.stratify(n_layers=5):
        phi = f"{s.phi_deg:.1f}" if s.phi_deg is not None else "—"
        cu = f"{s.c_u_kPa:.1f}" if s.c_u_kPa is not None else "—"
        print(f"  {s.z_top:5.1f} {s.z_bot:5.1f} {s.q_t_avg_MPa:9.2f} {s.I_c_avg:5.2f} {s.sbt_zone.name:<18} {phi:>6} {cu:>9} {s.E_MPa:8.1f}")
    print("Límites: bandas de igual espesor (no se detectan contactos), I_c con Q_t (exponente n = 1), E = α·(q_t − σ'_v0) "
          "con α fijo (5 en arena, 2 en arcilla; el docstring del módulo cita una α variable con I_c que no se aplica) "
          "y N_kt = 14 sin calibrar.")


if __name__ == "__main__":
    main()
