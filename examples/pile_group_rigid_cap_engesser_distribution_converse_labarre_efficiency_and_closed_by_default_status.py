"""Grupo de pilotes bajo encepado rígido: reparto de Engesser, eficiencia de Converse-Labarre y estado de cálculo cerrado por defecto.

Grupo de 2 × 3 pilotes de Ø800 mm a s = 2,4 m (s/d = 3) bajo V = 6000 kN,
H_x = 600 kN y M_y = 2000 kN·m. `distribute_loads_rigid_cap`:
  N_i = V/n + M_x·y_i/Σy² + M_y·x_i/Σx²,  H_i = (H/n)/E_h
  Converse-Labarre: E = 1 − θ·[(n−1)·m + (m−1)·n]/(90·m·n), θ = atan(d/s) en grados
  lateral: E_h = 0,5 + 0,5·min(s/(6d), 1) (aproximación del módulo).
Cada comprobación lleva un estado (`CalculationStatus`): si falta la capacidad
de una dirección con demanda en ella, el resultado es NO_CALCULADO, nunca un
aprobado. Se recalculan a mano los axiles y la eficiencia.

Ejecutar:  python examples/pile_group_rigid_cap_engesser_distribution_converse_labarre_efficiency_and_closed_by_default_status.py
"""
import math

from foundationcalc.analysis.pile_group import (
    converse_labarre_efficiency, distribute_loads_rigid_cap, rectangular_group,
)


def main() -> None:
    V, Hx, My = 6000.0, 600.0, 2000.0
    s, d = 2.4, 0.8
    g = rectangular_group(n_rows=2, n_cols=3, spacing_m=s, diameter_m=d)
    r = distribute_loads_rigid_cap(g, V_kN=V, H_x_kN=Hx, M_y_kNm=My)
    Ix2 = sum(p.x_m ** 2 for p in g.piles)
    theta = math.degrees(math.atan(d / s))
    E = 1 - theta * ((2 - 1) * 3 + (3 - 1) * 2) / (90 * 3 * 2)
    Eh = 0.5 + 0.5 * min(s / d / 6, 1)
    print(f"Grupo 2 × 3, Ø{d * 1000:.0f} mm a {s} m; V = {V:.0f} kN, H_x = {Hx:.0f} kN, M_y = {My:.0f} kN·m")
    print(f"A mano: Σx² = {Ix2:.2f} m²; N = {V / 6:.1f} ± {My:.0f}·2,4/{Ix2:.2f} = {V / 6:.1f} ± {My * 2.4 / Ix2:.1f} kN; "
          f"θ = {theta:.3f}°, E = {E:.4f}; E_h = {Eh:.3f}; H_i = {Hx / 6:.1f}/{Eh:.3f} = {Hx / 6 / Eh:.1f} kN")
    print(f"Paquete: E = {r.axial_efficiency:.4f}, E_h = {r.lateral_efficiency:.3f}")
    print(f"  {'pilote':<6} {'x':>5} {'y':>5} {'N [kN]':>8} {'H [kN]':>7}")
    for f in r.forces:
        print(f"  {f.pile_name:<6} {f.x_m:5.1f} {f.y_m:5.1f} {f.N_kN:8.1f} {math.hypot(f.H_x_kN, f.H_y_kN):7.1f}")
    print(f"Sin capacidades declaradas: estado {r.status.value}, faltan {r.missing_inputs}, all_ok = {r.all_ok}\n")

    g2 = rectangular_group(n_rows=2, n_cols=3, spacing_m=s, diameter_m=d, axial_capacity_kN=1600.0,
                           tension_capacity_kN=400.0, lateral_capacity_kN=180.0)
    r2 = distribute_loads_rigid_cap(g2, V_kN=V, H_x_kN=Hx, M_y_kNm=My)
    print(f"Con capacidades por pilote (1600 compresión, 400 tracción, 180 lateral):")
    print(f"  axial {r2.group_axial_utilization:.3f} = {max(f.N_kN for f in r2.forces):.1f}/(1600·{E:.4f}); "
          f"lateral {r2.group_lateral_utilization:.3f}; gobierna {r2.governing_pile}; estado {r2.status.value}")
    r3 = distribute_loads_rigid_cap(g2, V_kN=1500.0, M_y_kNm=6000.0)
    print(f"  Con V = 1500 kN y M_y = 6000 kN·m hay tracción: N_min = {-r3.N_max_tension:.1f} kN, util. tracción "
          f"{r3.group_tension_utilization:.2f}, estado {r3.status.value}\n")

    print("Eficiencia de Converse-Labarre frente a s/d (grupo 2 × 3):")
    for sd in (2.0, 2.5, 3.0, 3.5, 3.99, 4.0, 5.0):
        th = math.degrees(math.atan(1 / sd))
        formula = 1 - th * 7 / 540
        print(f"  s/d = {sd:4.2f}: paquete {converse_labarre_efficiency(2, 3, sd * d, d):.3f}, fórmula {formula:.3f}")
    print("  El módulo devuelve E = 1 para s/d ≥ 4 aunque la fórmula siga dando < 1 (salto en s/d = 4) y limita E ≥ 0,5: "
          "criterio del módulo, a revisar con la práctica local.")
    print("Límites: encepado rígido y pilotes verticales iguales; reparto lateral uniforme dividido por E_h; la E_h de "
          "Mokwa y Duncan es una aproximación lineal, no sus p-multiplicadores por fila.")


if __name__ == "__main__":
    main()
