"""Pantallas y excavaciones: pantalla con un puntal por soporte libre, puntales con presión aparente de Peck, levantamiento de fondo y anclajes.

1) Pantalla de 10 m de excavación en arena (φ' = 32°, γ = 20 kN/m³) con un
   puntal en cabeza (`DiaphragmWallDesigner`, soporte libre). Comprobación a
   mano con k = γ_G·K_a·γ:
     P_a = k·(H + D)²/2,  M_a = P_a·⅔·(H + D) respecto al puntal,
     P_p = ½·K_p·γ·D²/γ_R;e con brazo H + ⅔·D,
     P_p,mob = M_a/brazo (equilibrio de momentos), T = P_a − P_p,mob,
     cortante nulo en z0 = √(2T/k) y M_max = ⅔·T·z0 (si z0 < H).
   Hasta la 1.1.0 el puntal salía de restar TODO el pasivo disponible y el
   momento de la fórmula de carga uniforme T²/(2·q_max): con D = 7 m daba
   T = 60 kN/m y M = 13 kN·m/m frente a 272 kN/m y 1472 kN·m/m.
2) Excavación apuntalada de 9 m (`excavations`): envolvente de presión
   aparente de Terzaghi y Peck en arena (p = 0,65·K_a·γ·H, rectangular) y en
   arcilla blanda, fuerzas en puntales por áreas tributarias, y factor de
   seguridad frente a levantamiento de fondo FS = N_c·c_u/(γ·H + q).
3) Muro anclado (`AnchoredWallDesigner`), declarado como heurístico: reparte
   el empuje total a partes iguales entre niveles y dimensiona la longitud de
   bulbo para que la utilización sea 1 por construcción.

Ejecutar:  python examples/embedded_walls_diaphragm_free_earth_support_prop_force_moment_strut_loads_apparent_pressure_basal_heave_and_anchors.py
"""
import math

from foundationcalc.codes.eurocode7 import DesignApproach, LimitState, get_partial_factors
from foundationcalc.design.anchored_wall import AnchoredWallDesigner, AnchoredWallGeometry, AnchoredWallLoading, AnchorLevel
from foundationcalc.design.diaphragm_wall import DiaphragmWallDesigner, DiaphragmWallGeometry, DiaphragmWallLoading
from foundationcalc.excavations import apparent_earth_pressure, basal_heave_clay, strut_force, terzaghi_peck_heave


def main() -> None:
    H, phi, g = 10.0, 32.0, 20.0
    load = DiaphragmWallLoading(phi_deg=phi, gamma_kN_m3=g)
    print(f"Pantalla H = {H} m, φ' = {phi}°, γ = {g} kN/m³, puntal en cabeza, DA2 (γ_G = 1,35, γ_R;e = 1,4)")
    print(f"  {'ficha D':>7} {'P_a,d':>7} {'P_p,d':>7} {'F = M_p/M_a':>11} {'P_p,mob':>7} {'T puntal':>8} {'M_max':>7} {'z(M_max)':>8}")
    for D in (5.0, 6.0, 7.0, 8.0, 9.0):
        r = DiaphragmWallDesigner(DiaphragmWallGeometry(H_excavation=H, embedment_m=D, prop_levels_m=[0.0]), load).check()
        flag = "" if r.overturning_safety_factor >= 1.0 else "  <- ficha insuficiente (F < 1)"
        print(f"  {D:7.1f} {r.P_active_kN_per_m:7.1f} {r.P_passive_kN_per_m:7.1f} {r.overturning_safety_factor:11.3f} "
              f"{r.P_passive_mobilised_kN_per_m:7.1f} {r.prop_forces_kN_per_m[0]:8.1f} {r.M_max_kNm_per_m:7.0f} {r.z_of_M_max_m:8.2f}{flag}")
    r = DiaphragmWallDesigner(DiaphragmWallGeometry(H_excavation=H, embedment_m=7.0, prop_levels_m=[0.0]), load).check()
    print(f"  Ficha para F = 1,5 sobre valores de cálculo: D = {r.embedment_required_m:.2f} m "
          "(el 1,5 se suma a los coeficientes parciales: doble seguridad heredada del módulo)")

    Ka, Kp = math.tan(math.radians(45 - phi / 2)) ** 2, math.tan(math.radians(45 + phi / 2)) ** 2
    k = 1.35 * Ka * g
    D = 7.0
    Pa = k * (H + D) ** 2 / 2
    Ma = Pa * 2 / 3 * (H + D)
    Pp = 0.5 * Kp * g * D ** 2 / 1.4
    arm = H + 2 * D / 3
    T = Pa - Ma / arm
    z0 = math.sqrt(2 * T / k)
    print(f"  A mano (D = 7 m): K_a = {Ka:.4f}, K_p = {Kp:.3f}, k = 1,35·K_a·γ = {k:.3f} kN/m³; P_a = {Pa:.1f}, "
          f"M_a = {Ma:.0f}, P_p = {Pp:.1f}, F = {Pp * arm / Ma:.3f}; T = {Pa:.1f} − {Ma:.0f}/{arm:.3f} = {T:.1f} kN/m; "
          f"z0 = {z0:.2f} m, M_max = ⅔·T·z0 = {2 / 3 * T * z0:.0f} kN·m/m")
    print(f"  Fórmulas anteriores a la 1.1.0: T = P_a − P_p = {Pa - Pp:.1f} kN/m y M = T²/(2·k·(H + D)) = "
          f"{(Pa - Pp) ** 2 / (2 * k * (H + D)):.1f} kN·m/m")
    for da in (DesignApproach.DA1_C1, DesignApproach.DA1_C2, DesignApproach.DA3):
        rr = DiaphragmWallDesigner(DiaphragmWallGeometry(H_excavation=H, embedment_m=7.0, prop_levels_m=[0.0]), load,
                                   design_approach=da).check()
        pf = get_partial_factors(da, LimitState.GEO)
        print(f"  {da.value:<6}: γ_φ = {pf.soil.gamma_phi}, γ_R;e = {pf.resistance.gamma_Re}: F = {rr.overturning_safety_factor:.3f}, "
              f"T = {rr.prop_forces_kN_per_m[0]:.1f} kN/m, M_max = {rr.M_max_kNm_per_m:.0f} kN·m/m")

    print("\nExcavación apuntalada de 9 m, puntales a 1,5 / 4,5 / 7,5 m, separación horizontal 4 m:")
    He, levels = 9.0, (1.5, 4.5, 7.5)
    sand = apparent_earth_pressure(He, 19.0, soil_type="sand", phi=34.0)
    forces = strut_force(sand, levels, spacing=4.0)
    total = sum(f["force"] for f in forces)
    print(f"  arena φ' = 34°: p = 0,65·K_a·γ·H = 0,65·{sand['Ka']:.4f}·19·9 = {sand['p_max']:.2f} kPa; "
          + ", ".join(f"z = {f['z']} m ({f['z_top']:.1f}–{f['z_bot']:.1f}): {f['force']:.0f} kN" for f in forces))
    print(f"  suma de puntales {total:.0f} kN = p·H·s = {sand['p_max'] * He * 4.0:.0f} kN (sin base: el último puntal "
          "recoge hasta el fondo)")
    for cu in (25.0, 40.0):
        clay = apparent_earth_pressure(He, 18.0, c_u=cu, soil_type="soft_clay")
        fc = strut_force(clay, levels, spacing=4.0)
        print(f"  arcilla blanda c_u = {cu:.0f} kPa: N_s = γH/c_u = {clay['Ns']:.2f}, K = 1 − 0,4·4·c_u/(γH) = {clay['Kp']:.3f}, "
              f"p = {clay['p_max']:.1f} kPa; puntales " + ", ".join(f"{f['force']:.0f}" for f in fc) + " kN")
        hv = terzaghi_peck_heave(B=12.0, L=60.0, gamma=18.0, c_u=cu, H=He, q_surcharge=10.0)
        hv_sq = terzaghi_peck_heave(B=12.0, L=12.0, gamma=18.0, c_u=cu, H=He, q_surcharge=10.0)
        print(f"    levantamiento de fondo: zanja 12 × 60 m N_c = {hv['Nc']:.2f}, FS = {hv['FS']:.2f}; "
              f"recinto 12 × 12 m N_c = {hv_sq['Nc']:.2f}, FS = {hv_sq['FS']:.2f} -> "
              f"{'aceptable' if min(hv['FS'], hv_sq['FS']) >= 1.5 else 'insuficiente'} frente al FS = 1,5 habitual")
    b1 = terzaghi_peck_heave(B=12.0, L=59.9, gamma=18.0, c_u=25.0, H=He)["Nc"]
    b2 = terzaghi_peck_heave(B=12.0, L=60.0, gamma=18.0, c_u=25.0, H=He)["Nc"]
    print(f"  Ojo: N_c salta de {b1:.2f} (L = 59,9 m) a {b2:.2f} (L = 60 m = 5B) porque el módulo mezcla 5,7·(1 + 0,2B/L) "
          "con 5,14 de faja (sin contrastar)." )
    print(f"  basal_heave_clay con N_c = 5,14: FS = 5,14·25/(18·9) = {basal_heave_clay(He, 12.0, 18.0, 25.0)['FS']:.3f}")

    print("\nMuro anclado de 8 m en arena (φ' = 32°, γ = 19, q = 10 kPa), dos niveles de anclajes activos a 2 y 5 m cada 2,5 m:")
    geo = AnchoredWallGeometry(H_excavation=8.0, embedment_m=2.0, anchor_levels=[
        AnchorLevel(z_below_top_m=2.0, horizontal_spacing_m=2.5, bond_zone_soil="dense_sand"),
        AnchorLevel(z_below_top_m=5.0, horizontal_spacing_m=2.5, bond_zone_soil="dense_sand"),
    ])
    aw = AnchoredWallDesigner(geo, AnchoredWallLoading(phi_deg=32.0, gamma_kN_m3=19.0, surcharge_q=10.0)).check()
    Ka8 = math.tan(math.radians(29.0)) ** 2
    P_hand = 1.35 * 0.65 * Ka8 * 19 * 8 * 8 + 1.35 * 10 * 0.5 * 8
    print(f"  P_total = 1,35·0,65·K_a·γ·H·H + 1,35·0,5·q·H = {P_hand:.1f} kN/m (paquete {aw.P_total_kN_per_m:.1f})")
    for a in aw.anchors:
        print(f"  z = {a.z_m} m: T_d = {a.T_design_kN_per_anchor:.0f} kN/anclaje (P/2·2,5/cos 15°), libre {a.free_length_m:.2f} m, "
              f"bulbo {a.bond_length_m:.2f} m, utilización {a.bond_utilization:.3f}, bloqueo {a.lock_off_load_kN:.0f} kN")
    print("  Los dos niveles reciben lo mismo aunque estén a 2 y 5 m, y la utilización del bulbo vale 1 por "
          "construcción: el módulo dimensiona, no verifica. Para reparto por áreas tributarias usa `strut_force`.")
    print("Límites: soporte libre con un puntal (con varios, reparto a partes iguales sin equilibrio de momentos); "
          "sin cohesión ni agua en la pantalla (el módulo ahora lo rechaza); envolvente de arcilla blanda rectangular "
          "desde coronación; q_s, γ_a = 1,5 y K = 0,5 de la sobrecarga del muro anclado sin contrastar.")


if __name__ == "__main__":
    main()
