# -*- coding: utf-8 -*-
"""Tank wall hydrostatic loads — Pynite example.

Adapted from Engineering-Fundamentals (Flocode) — MIT
    https://github.com/flocode/Engineering-Fundamentals

Demuestra cómo aplicar cargas hidrostáticas (presión triangular) sobre
un muro de tanque modelado con placas rectangulares. Patrón reusable
para muros de contención y cimentaciones bajo nivel freático.

Ejecutar:
    python -m foundationdesignjm.examples.pynite.hydrostatic_loads
"""
from __future__ import annotations


def run() -> dict:
    """Ejecuta el análisis y retorna desplazamientos extremos."""
    from Pynite.FEModel3D import FEModel3D  # import diferido

    model = FEModel3D()

    # Concreto 4500 psi (unidades: psf, ft)
    E = 57000 * (4500) ** 0.5 * 12 ** 2  # psf
    G = 0.4 * E
    nu = 0.17
    rho = 150  # pcf
    model.add_material("Concrete", E, G, nu, rho)

    mesh_size = 1.0     # ft
    width = 25.0        # ft
    height = 15.0       # ft
    t = 1.0             # ft
    HL = 12.5           # ft (liquid height)

    model.add_rectangle_mesh(
        "MSH1", mesh_size, width, height, t, "Concrete",
        kx_mod=1, ky_mod=1, origin=[0, 0, 0], plane="XY",
        y_control=[HL], element_type="Rect",
    )
    model.Meshes["MSH1"].generate()

    # Presión hidrostática: p(y) = γ_water · (HL - y)  con γ = 62.4 pcf
    for element in list(model.Quads.values()) + list(model.Plates.values()):
        Yavg = (
            element.i_node.Y + element.j_node.Y +
            element.m_node.Y + element.n_node.Y
        ) / 4
        if Yavg < HL:
            pressure = 62.4 * (HL - Yavg)  # psf
            if model.Meshes["MSH1"].element_type == "Rect":
                model.add_plate_surface_pressure(element.name, pressure, case="F")
            else:
                model.add_quad_surface_pressure(element.name, pressure, case="F")

    # Empotramientos en bordes inferior, izquierdo, derecho
    for node in model.Nodes.values():
        if (round(node.Y, 10) == 0
                or round(node.X, 10) == 0
                or round(node.X, 10) == width):
            model.def_support(node.name, True, True, True, True, True, True)

    model.add_load_combo("1.4F", {"F": 1.4})
    model.analyze(log=False, check_statics=True)

    dz_vals = [node.DZ["1.4F"] for node in model.Nodes.values()]
    return {
        "max_DZ_ft": float(max(dz_vals)),
        "min_DZ_ft": float(min(dz_vals)),
        "n_nodes": len(model.Nodes),
        "liquid_height_ft": HL,
        "wall_width_ft": width,
        "wall_height_ft": height,
    }


def main() -> None:
    res = run()
    print("=== Tank wall hydrostatic loads (Pynite) ===")
    print(f"Wall {res['wall_width_ft']:.0f} x {res['wall_height_ft']:.0f} ft, "
          f"liquid height {res['liquid_height_ft']:.1f} ft")
    print(f"Nodes              : {res['n_nodes']}")
    print(f"Max DZ (1.4F)      : {res['max_DZ_ft']:.6f} ft")
    print(f"Min DZ (1.4F)      : {res['min_DZ_ft']:.6f} ft")


if __name__ == "__main__":
    main()
