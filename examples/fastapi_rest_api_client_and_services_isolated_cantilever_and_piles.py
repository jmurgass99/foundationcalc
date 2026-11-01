"""API REST FastAPI de foundationcalc: endpoints de zapatas, muros, pilotes, capacidad portante y empujes.

Verifica la capa de servicios REST mediante TestClient síncrono sobre la aplicación FastAPI
canónica (`foundationcalc.api.app:app`), contrastando las respuestas JSON contra llamadas
directas a los servicios analíticos del paquete.
"""
from __future__ import annotations

import warnings
from fastapi.testclient import TestClient

from foundationcalc import __version__
from foundationcalc.api.app import app
from foundationcalc.services import footings, walls, piles, bearing, seismic


def main() -> None:
    print(f"=== foundationcalc v{__version__} — API REST FastAPI ===")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with TestClient(app) as client:
            # 1. Root metadata
            r_root = client.get("/")
            assert r_root.status_code == 200, f"Error en /: {r_root.text}"
            root_data = r_root.json()
            print(f"\n1. GET / -> Nombre: {root_data.get('name')}")
            print(f"   Endpoints registrados: {len(root_data.get('endpoints', []))}")
            for ep in root_data.get("endpoints", []):
                print(f"     - {ep}")

            # 2. Zapata aislada
            footing_payload = {
                "L_x": 2.5,
                "L_y": 2.5,
                "thickness": 0.6,
                "depth": 1.0,
                "column_b": 0.45,
                "column_h": 0.45,
                "fc_MPa": 30.0,
                "fy_MPa": 500.0,
                "N": 1500.0,
                "M_x": 120.0,
                "M_y": 80.0,
                "q_allow_kPa": 300.0,
            }
            r_footing = client.post("/api/footings/isolated", json=footing_payload)
            assert r_footing.status_code == 200, f"Error en /api/footings/isolated: {r_footing.text}"
            res_f = r_footing.json()
            pressures = res_f["pressures"]
            print(f"\n2. POST /api/footings/isolated (Zapata 2,5×2,5 m, N = 1500 kN):")
            print(f"   q_max = {pressures['q_max']:.2f} kPa, q_min = {pressures['q_min']:.2f} kPa, q_avg = {pressures['q_avg']:.2f} kPa")
            print(f"   Punzonamiento DCR = {res_f['punching']['DCR']:.3f} (Vu = {res_f['punching']['Vu']:.1f} kN, Vc = {res_f['punching']['Vc']:.1f} kN)")
            print(f"   Armado flexión X: As_req = {res_f['flexure_x']['As_required']:.0f} mm², elegido = {res_f['flexure_x']['As_chosen']:.0f} mm²")
            print(f"   Armado flexión Y: As_req = {res_f['flexure_y']['As_required']:.0f} mm², elegido = {res_f['flexure_y']['As_chosen']:.0f} mm²")

            direct_footing = footings.design_isolated_footing(footings.IsolatedFootingInput(**footing_payload))
            assert abs(pressures["q_max"] - direct_footing.pressures["q_max"]) < 1e-3
            print(f"   [OK] Coincidencia exacta con footings.design_isolated_footing")

            # 3. Muro en ménsula
            wall_payload = {
                "H": 4.5,
                "base_width": 2.8,
                "stem_thickness": 0.35,
                "toe_width": 0.8,
                "heel_width": 1.65,
                "gamma_soil": 18.5,
                "phi_soil": 32.0,
                "surcharge_kPa": 10.0,
            }
            r_wall = client.post("/api/walls/cantilever", json=wall_payload)
            assert r_wall.status_code == 200, f"Error en /api/walls/cantilever: {r_wall.text}"
            res_w = r_wall.json()
            print(f"\n3. POST /api/walls/cantilever (Muro ménsula H = 4,5 m):")
            print(f"   FS deslizamiento = {res_w['sliding_FS']:.3f}")
            print(f"   FS vuelco        = {res_w['overturning_FS']:.3f}")
            print(f"   bearing_FS       = {res_w['bearing_FS']} (no evaluado por este servicio)")
            print(f"   Fuste: M_stem = {res_w['stem_design']['M_stem']:.1f} kN·m/m, espesor mín = {res_w['stem_design']['thickness_min_mm']:.0f} mm")

            direct_wall = walls.design_cantilever_wall(walls.CantileverWallInput(**wall_payload))
            assert abs(res_w["sliding_FS"] - direct_wall.sliding_FS) < 1e-4
            print(f"   [OK] Coincidencia exacta con walls.design_cantilever_wall")

            # 4. Pilote axial
            pile_payload = {
                "D": 0.8,
                "L": 15.0,
                "layers_qu_kPa": [40.0, 80.0],
                "layers_thickness": [5.0, 10.0],
                "Nq_tip": 9.0,
            }
            r_pile = client.post("/api/piles/axial", json=pile_payload)
            assert r_pile.status_code == 200, f"Error en /api/piles/axial: {r_pile.text}"
            res_p = r_pile.json()
            print(f"\n4. POST /api/piles/axial (Pilote Ø0,8 m, L = 15 m en arcilla):")
            print(f"   Q_skin      = {res_p['Q_skin_kN']:.1f} kN")
            print(f"   Q_tip       = {res_p['Q_tip_kN']:.1f} kN")
            print(f"   Q_ultimate  = {res_p['Q_ultimate_kN']:.1f} kN")
            print(f"   Q_allowable = {res_p['Q_allowable_kN']:.1f} kN (FS = {res_p['FS']:.1f})")
            assert abs(res_p["Q_ultimate_kN"] - (res_p["Q_skin_kN"] + res_p["Q_tip_kN"])) < 1e-3
            print(f"   [OK] Equilibrio de capacidad axial verificado")

            # 5. Capacidad portante multicapa
            bearing_payload = {
                "L_x": 2.5,
                "L_y": 2.5,
                "depth": 1.2,
                "method": "vesic",
                "layers": [
                    {"thickness": 2.0, "gamma": 18.0, "phi": 30.0, "c": 5.0},
                    {"thickness": 5.0, "gamma": 19.0, "phi": 35.0, "c": 0.0},
                ],
            }
            r_bearing = client.post("/api/bearing/multilayer", json=bearing_payload)
            assert r_bearing.status_code == 200, f"Error en /api/bearing/multilayer: {r_bearing.text}"
            res_b = r_bearing.json()
            print(f"\n5. POST /api/bearing/multilayer (Zapata 2,5×2,5 m, estrato Vesić):")
            print(f"   qu = {res_b['qu_kPa']:.2f} kPa, qa = {res_b['qa_kPa']:.2f} kPa (FS = {res_b['FS']:.1f})")

            # 6. Empuje sísmico Mononobe-Okabe
            mo_payload = {
                "H": 5.0,
                "gamma": 19.0,
                "phi": 34.0,
                "delta": 22.0,
                "beta": 0.0,
                "alpha": 0.0,
                "kh": 0.15,
                "kv": 0.05,
            }
            r_mo = client.post("/api/seismic/mononobe_okabe", json=mo_payload)
            assert r_mo.status_code == 200, f"Error en /api/seismic/mononobe_okabe: {r_mo.text}"
            res_mo = r_mo.json()
            print(f"\n6. POST /api/seismic/mononobe_okabe (H = 5 m, kh = 0,15, kv = 0,05):")
            print(f"   K_AE = {res_mo['K_AE']:.4f}, P_AE = {res_mo['P_AE_kN_per_m']:.2f} kN/m, theta = {res_mo['theta_deg']:.2f}°")

    print("\nLímites documentados:")
    print("  - Los endpoints de la API delegan en los servicios predimensionadores.")
    print("  - /api/footings/isolated usa tensiones admisibles frente a ACI 318-19, no Eurocódigo 7.")
    print("  - /api/walls/cantilever reporta bearing_FS como nulo (la capacidad portante debe verificarse con CantileverWallDesigner).")
    print("  - /api/bearing/multilayer es un servicio histórico/deprecado; la calculadora canónica es analysis.bearing_capacity.")


if __name__ == "__main__":
    main()
