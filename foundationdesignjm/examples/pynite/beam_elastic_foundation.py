# -*- coding: utf-8 -*-
"""Beam on elastic (Winkler) foundation — Pynite cross-validation.

Adapted from Engineering-Fundamentals (Flocode) — MIT
    https://github.com/flocode/Engineering-Fundamentals

Modela una viga de 25 ft con resortes de Winkler distribuidos cada 12"
(ks = 22.5 k/in) y carga puntual de 40 k en el centro. Sirve como
validación cruzada externa contra el modelo Winkler propio de FastSAP
(`foundationdesignjm/analysis/winkler.py`).

Ejecutar:
    python -m foundationdesignjm.examples.pynite.beam_elastic_foundation
"""
from __future__ import annotations


def run() -> dict:
    """Ejecuta el análisis y retorna las magnitudes clave."""
    from Pynite import FEModel3D  # import diferido (opcional dep)

    boef = FEModel3D()

    # Geometría (unidades: kips, in)
    L = 25 * 12  # in
    num_nodes = round(L / 12) + 1
    spacing = L / round(L / 12)

    # Rigidez del resorte de Winkler
    ks = 22.5  # k/in

    # Nodos + soportes (pin en extremos, resorte en interior)
    for i in range(num_nodes):
        boef.add_node("N" + str(i + 1), i * spacing, 0, 0)
        if i == 0 or i == num_nodes - 1:
            boef.def_support("N" + str(i + 1), True, True, True, True, False, False)
        else:
            boef.def_support_spring("N" + str(i + 1), "DY", ks, "-")

    # Material (acero A36)
    E = 29000  # ksi
    G = 11200  # ksi
    boef.add_material("Steel", E, G, 0.3, 490 / 1000 / 12**3)

    # Sección W8x35
    A, Iz, Iy, J = 10.3, 127.0, 42.6, 0.769
    boef.add_section("M1Section", A, Iy, Iz, J)
    boef.add_member("M1", "N1", "N" + str(num_nodes), "Steel", "M1Section")

    # Carga puntual en el centro
    if num_nodes % 2 == 0:
        boef.add_member_pt_load("M1", "Fy", -40, L / 2)
    else:
        mid_node = "N" + str(int(num_nodes / 2))
        boef.add_node_load(mid_node, "FY", -40)

    boef.analyze(log=False, check_statics=True)

    return {
        "d_min_in": float(boef.members["M1"].min_deflection("dy")),
        "M_min_kip_in": float(boef.members["M1"].min_moment("Mz")),
        "M_max_kip_in": float(boef.members["M1"].max_moment("Mz")),
        "L_in": L,
        "ks_kip_per_in": ks,
        "num_springs": num_nodes - 2,
    }


def main() -> None:
    res = run()
    print("=== Beam on elastic foundation (Pynite cross-validation) ===")
    print(f"Length              : {res['L_in']:.1f} in ({res['L_in']/12:.1f} ft)")
    print(f"Spring stiffness ks : {res['ks_kip_per_in']:.2f} k/in")
    print(f"Interior springs    : {res['num_springs']}")
    print(f"Min deflection      : {res['d_min_in']:.4f} in")
    print(f"Min moment Mz       : {round(res['M_min_kip_in'])} k-in")
    print(f"Max moment Mz       : {round(res['M_max_kip_in'])} k-in")


if __name__ == "__main__":
    main()
