"""Ensayo SPT: correcciones de energía y de sobrecarga (N60, N1(60)) y correlaciones de φ', D_R, c_u y E.

Sondeo con maza de rendimiento ER = 70 % (cada golpeo se lleva a N60 = N·ER/60)
en arena hasta 9 m y arcilla debajo (σ'v0 de cada cota dado). Correcciones
(módulo `analysis.spt`):
  C_N = √(p_a/σ'v0), acotado a [0,5; 2,0] (Liao y Whitman 1986)
  N1(60) = C_N·N60
Correlaciones:
  φ' = √(20·N1(60)) + 20 (Hatanaka y Uchida 1996); φ' = √(15·N1(60)) + 15 (JRA 1990);
  φ' = 27,1 + 0,30·N60 − 0,00054·N60² (ajuste de la gráfica de Peck, Hanson y Thornburn 1974);
  D_R = √(N1(60)/60) (Skempton 1986); c_u = f1·N60 con f1 = 4,5 para PI ≥ 30 (Stroud 1974);
  E = 0,766·N60 MPa en arena (Schmertmann 1970) y 0,5·(N60 + 15) (Bowles 1996).
Se comprueba a mano la lectura de 6 m.

Ejecutar:  python examples/spt_energy_and_overburden_corrections_n60_n1_60_phi_hatanaka_uchida_jra_dr_skempton_cu_stroud.py
"""
import math

from foundationcalc.analysis.spt import (
    E_bowles, E_schmertmann, SPTReading, SoilTypeSPT, derive_parameters, phi_japan_road_association,
    phi_peck_hanson_thornburn,
)


def main() -> None:
    readings = [
        SPTReading(depth_m=1.5, N_raw=8, sigma_v0_eff_kPa=27.0, energy_ratio_ER=70.0, soil_type=SoilTypeSPT.SAND),
        SPTReading(depth_m=3.0, N_raw=14, sigma_v0_eff_kPa=50.0, energy_ratio_ER=70.0, soil_type=SoilTypeSPT.SAND),
        SPTReading(depth_m=6.0, N_raw=22, sigma_v0_eff_kPa=80.0, energy_ratio_ER=70.0, soil_type=SoilTypeSPT.SAND),
        SPTReading(depth_m=9.0, N_raw=31, sigma_v0_eff_kPa=110.0, energy_ratio_ER=70.0, soil_type=SoilTypeSPT.SAND),
        SPTReading(depth_m=12.0, N_raw=12, sigma_v0_eff_kPa=140.0, energy_ratio_ER=70.0, soil_type=SoilTypeSPT.CLAY),
        SPTReading(depth_m=15.0, N_raw=16, sigma_v0_eff_kPa=170.0, energy_ratio_ER=70.0, soil_type=SoilTypeSPT.CLAY),
    ]
    print(f"{'z [m]':>5} {'suelo':<5} {'N':>3} " + f"{'σ_v0_eff':>8} {'N60':>6} {'N1(60)':>7} {'φ H-U':>6} {'φ JRA':>6} {'φ PHT':>6} "
          f"{'D_R %':>5} {'c_u':>6} {'E Schm.':>7} {'E Bowles':>8}")
    for r in readings:
        d = derive_parameters(r, plasticity_index=35.0)
        sand = r.soil_type == SoilTypeSPT.SAND
        phi_jra = f"{phi_japan_road_association(d.N_1_60):6.1f}" if sand else f"{'—':>6}"
        phi_pht = f"{phi_peck_hanson_thornburn(d.N_60):6.1f}" if sand else f"{'—':>6}"
        phi = f"{d.phi_deg:6.1f}" if d.phi_deg is not None else f"{'—':>6}"
        dr = f"{d.relative_density_pct:5.0f}" if d.relative_density_pct is not None else f"{'—':>5}"
        cu = f"{d.c_u_kPa:6.1f}" if d.c_u_kPa is not None else f"{'—':>6}"
        Eb = E_bowles(d.N_60, r.soil_type)
        print(f"{r.depth_m:5.1f} {r.soil_type.value:<5} {r.N_raw:3d} {r.sigma_v0_eff_kPa:5.0f} {d.N_60:6.2f} {d.N_1_60:7.2f} "
              f"{phi} {phi_jra} {phi_pht} {dr} {cu} {d.E_MPa:7.1f} {Eb:8.1f}")

    r = readings[2]
    N60 = r.N_raw * r.energy_ratio_ER / 60
    CN = min(max(math.sqrt(100 / r.sigma_v0_eff_kPa), 0.5), 2.0)
    N160 = CN * N60
    print(f"\nA mano, 6 m: N60 = {r.N_raw}·70/60 = {N60:.3f}; C_N = √(100/{r.sigma_v0_eff_kPa:.0f}) = {CN:.4f}; "
          f"N1(60) = {N160:.3f}")
    print(f"  φ' (H-U) = √(20·{N160:.3f}) + 20 = {math.sqrt(20 * N160) + 20:.2f}°; D_R = √({N160:.3f}/60) = "
          f"{math.sqrt(N160 / 60) * 100:.1f} %; E = 0,766·{N60:.2f} = {0.766 * N60:.2f} MPa "
          f"(paquete {E_schmertmann(N60):.2f})")
    d = derive_parameters(readings[2])
    spread = [d.phi_deg, phi_japan_road_association(d.N_1_60), phi_peck_hanson_thornburn(d.N_60)]
    print(f"  Las tres correlaciones de φ' en 6 m van de {min(spread):.1f}° a {max(spread):.1f}°: "
          f"{max(spread) - min(spread):.1f}° de dispersión entre autores para el mismo golpeo.")
    print("Límites: C_N de Liao y Whitman sin corrección por diámetro, varillaje ni tomamuestras; correlaciones "
          "empíricas sin calibración local; E de Schmertmann para arena se aplica igual a arena seca y saturada.")


if __name__ == "__main__":
    main()
