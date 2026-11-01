"""Consolidación unidimensional de Terzaghi: U(T_v) exacta frente a las aproximaciones, asiento NC/OC y tiempos.

1) U(T_v) = 1 − Σ 2/M²·exp(−M²·T_v), M = π(2m+1)/2 (serie, `U_from_Tv`) frente
   a √(4T_v/π) y 1 − (8/π²)·exp(−π²T_v/4); inversas T_v(U) de Casagrande y
   Taylor. Valores de referencia: T_v50 = 0,197, T_v90 = 0,848.
2) Arcilla de 4 m drenada por las dos caras: e0 = 1,10, Cc = 0,35, Cr = 0,05,
   σ'0 = 60 kPa en el centro, σ'p = 90 kPa (OCR 1,5), Δσ = 80 kPa,
   cv = 2,0 m²/año. Asiento que cruza la presión de preconsolidación:
   s = H·Cr/(1+e0)·log(σ'p/σ'0) + H·Cc/(1+e0)·log((σ'0+Δσ)/σ'p), a mano.
3) t50 y t90 y la curva s(t); las dos implementaciones del paquete
   (`analysis.consolidacion_1d` y `consolidacion_1d`, normalmente consolidada)
   se comparan entre sí.

Ejecutar:  python examples/terzaghi_consolidation_u_tv_series_vs_approximations_oc_nc_settlement_and_time_to_90_percent.py
"""
import math

from foundationcalc.analysis.consolidation import (
    ClayLayer, Tv_from_U, U_from_Tv, consolidation_curve, settlement_consolidation, time_to_consolidation,
)
from foundationcalc.analysis.consolidacion_1d import ConsolidationInput as CI_a, consolidate
from foundationcalc.consolidacion_1d import ConsolidationInput as CI_b, evaluate_consolidation


def main() -> None:
    print(f"{'T_v':>6} {'U serie':>8} {'√(4T/π)':>8} {'1−8/π²·e':>9}")
    for Tv in (0.01, 0.05, 0.1, 0.197, 0.3, 0.5, 0.848, 1.2):
        a1 = math.sqrt(4 * Tv / math.pi)
        a2 = 1 - 8 / math.pi ** 2 * math.exp(-math.pi ** 2 * Tv / 4)
        print(f"{Tv:6.3f} {U_from_Tv(Tv):8.4f} {a1:8.4f} {a2:9.4f}")
    print(f"Inversa (Casagrande/Taylor): T_v(50 %) = {Tv_from_U(0.5):.4f}, T_v(90 %) = {Tv_from_U(0.9):.4f} "
          "(referencias 0,197 y 0,848)\n")

    H, e0, Cc, Cr, s0, sp, ds, cv = 4.0, 1.10, 0.35, 0.05, 60.0, 90.0, 80.0, 2.0
    clay = ClayLayer(thickness_m=H, e0=e0, C_c=Cc, C_r=Cr, OCR=sp / s0, sigma_p_kPa=sp, c_v_m2_per_year=cv)
    s = settlement_consolidation(clay, s0, ds)
    hand = H * Cr / (1 + e0) * math.log10(sp / s0) + H * Cc / (1 + e0) * math.log10((s0 + ds) / sp)
    print(f"Arcilla H = {H} m (doble drenaje), e0 = {e0}, Cc = {Cc}, Cr = {Cr}, σ'0 = {s0:.0f}, σ'p = {sp:.0f}, Δσ = {ds:.0f} kPa")
    print(f"  a mano: {H}·{Cr}/{1 + e0:.2f}·log({sp:.0f}/{s0:.0f}) + {H}·{Cc}/{1 + e0:.2f}·log({s0 + ds:.0f}/{sp:.0f}) = {hand * 1000:.1f} mm")
    print(f"  paquete: {s * 1000:.1f} mm")
    for d_, label in ((20.0, "sin llegar a σ'p"), (200.0, "muy por encima de σ'p")):
        print(f"  con Δσ = {d_:.0f} kPa ({label}): {settlement_consolidation(clay, s0, d_) * 1000:.1f} mm")
    nc = ClayLayer(thickness_m=H, e0=e0, C_c=Cc, C_r=Cr, OCR=1.0, sigma_p_kPa=s0, c_v_m2_per_year=cv)
    print(f"  si fuese normalmente consolidada: {settlement_consolidation(nc, s0, ds) * 1000:.1f} mm "
          f"({settlement_consolidation(nc, s0, ds) / s:.1f} veces más)\n")

    t50, t90 = time_to_consolidation(clay, 0.5), time_to_consolidation(clay, 0.9)
    print(f"H_dr = {clay.H_dr_m} m: t50 = T_v50·H_dr²/cv = {Tv_from_U(0.5):.4f}·{clay.H_dr_m}²/{cv} = {t50:.3f} años "
          f"({t50 * 365:.0f} días); t90 = {t90:.3f} años ({t90 * 365:.0f} días)")
    curve = consolidation_curve(clay, s, t_max_years=2.0, n_points=9)
    print("  " + "  ".join(f"t = {t:.2f} a: {u * s * 1000:.0f} mm" for t, u in zip(curve.times_years, curve.U)))

    a = consolidate(CI_a(H_layer_m=H, sigma_v0_kPa=s0, delta_sigma_kPa=ds, Cc=Cc, e0=e0, cv_m2_per_year=cv))
    b = evaluate_consolidation(CI_b(H_layer_m=H, sigma_v_0_kPa=s0, delta_sigma_kPa=ds, Cc=Cc, e_0=e0, cv_m2_per_year=cv))
    print(f"\nDos módulos duplicados (NC): analysis.consolidacion_1d S_c = {a.Sc_mm:.1f} mm, t90 = {a.t_90_days:.0f} d; "
          f"consolidacion_1d S_c = {b.Sc_mm:.1f} mm, t90 = {b.t_90pct_days:.0f} d "
          f"(el segundo usa 365,25 días/año y el primero 365). Asiento NC a mano: "
          f"{H * Cc / (1 + e0) * math.log10((s0 + ds) / s0) * 1000:.1f} mm.")


if __name__ == "__main__":
    main()
