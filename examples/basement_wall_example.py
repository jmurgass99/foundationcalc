"""Design of a single-basement RC wall.

Geometry (per metre run):
- 3.5 m high, 0.30 m thick.
- Bottom restrained by foundation slab → propped cantilever.
- Top restrained by the ground-floor slab → propped at top.

Backfill: phi = 30 deg, gamma = 19 kN/m3, surcharge = 10 kPa (parking
sidewalk traffic).

Axial load:
- N_min = 0 kN/m (during construction, before the upper structure).
- N_max = 200 kN/m (in service).
- e_top = 0.05 m, e_base = 0.10 m (axis offset).

Run with:   python -m examples.basement_wall_example
"""

from __future__ import annotations

from foundationdesignjm.design.basement_wall import (
    BasementWallDesigner,
    BasementWallGeometry,
    BasementWallLoading,
    PressureDiagram,
    SupportConfig,
)


def main() -> None:
    geo = BasementWallGeometry(
        height=3.5, thickness=0.30,
        eccentricity_top=0.05, eccentricity_base=0.10,
    )
    load = BasementWallLoading(
        phi_deg=30, gamma_soil=19, surcharge_q=10,
        water_height=0,
        N_min_kN_per_m=0, N_max_kN_per_m=200,
    )

    print("=" * 78)
    print(f"FoundationDesignJm - Basement wall (H={geo.height} m, t={geo.thickness} m)")
    print("=" * 78)
    print(f"K_0 = {load.K0:.3f}  (phi={load.phi_deg} deg, OCR={load.OCR})")
    print(f"Surcharge q = {load.surcharge_q} kPa,  water = {load.water_height} m")
    print(f"N_min = {load.N_min_kN_per_m} kN/m,  N_max = {load.N_max_kN_per_m} kN/m,  "
          f"e_top = {geo.eccentricity_top} m, e_base = {geo.eccentricity_base} m")
    print()

    for support in [SupportConfig.PROPPED_CANTILEVER, SupportConfig.PINNED_PINNED,
                    SupportConfig.CANTILEVER]:
        for diagram in [PressureDiagram.TRIANGULAR, PressureDiagram.RECTANGULAR]:
            des = BasementWallDesigner(geo, load, support=support, pressure=diagram)
            res = des.solve()
            print(f"[{support.value:<19} | {diagram.value:<11}]  "
                  f"q_top={res.q_top_kPa:>5.1f}  q_base={res.q_base_kPa:>5.1f} kPa")
            print(f"   R_top = {res.R_top_kN_per_m:>6.1f} kN/m   "
                  f"R_base = {res.R_base_kN_per_m:>6.1f} kN/m   "
                  f"V_max = {res.V_max_kN:>5.1f} kN/m")
            print(f"   M_inner (inner-face rebar) = {res.M_inner_max_kNm:>+7.2f} kNm/m  "
                  f"at z = {res.z_of_M_inner_max_m:.2f} m")
            print(f"   M_outer (outer-face rebar) = {res.M_outer_max_kNm:>+7.2f} kNm/m  "
                  f"at z = {res.z_of_M_outer_max_m:.2f} m")
            print()


if __name__ == "__main__":
    main()
