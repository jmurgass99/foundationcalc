"""Losa de cimentación como placa de Mindlin sobre muelles de Winkler: comprobaciones de carga uniforme, límite rígido, equilibrio, despegue y exportación.

`MatFoundationSolver` discretiza la losa con elementos Q4 de Mindlin (flexión
2 × 2 y cortante MITC4), muelles k_s concentrados en los nudos y elimina los
muelles en tracción iterando. Hasta la 1.1.0 la cortante se integraba con un
punto y el modo espurio en damero contaminaba los asientos bajo los pilares
(en el caso 3 aparecían 82 nudos «despegados» y asientos casi el doble).
Comprobaciones independientes dentro del ejemplo:
1) presión uniforme q sobre losa libre: w = q/k_s en todos los nudos y
   momentos nulos;
2) losa muy rígida (h = 3 m) con pilares: asiento medio ≈ ΣP/(k_s·A) y giro
   del sólido rígido por la excentricidad de las cargas (w = w0 + θ·x);
3) losa real de 12 × 10 × 0,7 m con 6 pilares: la suma de reacciones de los
   muelles (k_s·área tributaria·w) iguala ΣP + q·A;
4) un pilar de esquina con tracción provoca despegue: se cuentan los nudos sin
   muelle y se vuelve a comprobar el equilibrio.
Exporta la malla y los resultados a JSON y a un .s2k mínimo de SAFE en
`examples/out/` (o en JM_EXAMPLES_OUT_DIR).

Ejecutar:  python examples/mat_foundation_mindlin_plate_on_winkler_springs_uniform_load_rigid_limit_equilibrium_uplift_and_exports.py
"""
import os
from pathlib import Path

import numpy as np

from foundationcalc import MatFoundationSolver
from foundationcalc.utils.json_export import export_mat_to_json
from foundationcalc.utils.safe_export import export_mat_to_safe

OUT = Path(os.environ.get("JM_EXAMPLES_OUT_DIR", Path(__file__).resolve().parent / "out"))


def tributary_areas(s: MatFoundationSolver) -> np.ndarray:
    dx, dy = s.length / s.nx, s.width / s.ny
    wx = np.full(s.nx + 1, dx); wx[[0, -1]] = dx / 2
    wy = np.full(s.ny + 1, dy); wy[[0, -1]] = dy / 2
    return np.outer(wy, wx).ravel()


def main() -> None:
    ks = 20000.0
    s1 = MatFoundationSolver(length=12.0, width=10.0, thickness=0.6, nx=12, ny=10, E_concrete=30e6, k_s=ks)
    s1.add_uniform_pressure(20.0)
    r1 = s1.solve()
    print(f"1) Carga uniforme q = 20 kPa, k_s = {ks:.0f} kN/m³: w = q/k_s = {20 / ks * 1000:.3f} mm")
    print(f"   paquete: w entre {r1.w.min() * 1000:.6f} y {r1.w.max() * 1000:.6f} mm; |M| máx = "
          f"{max(abs(r1.M_xx).max(), abs(r1.M_yy).max()):.2e} kN·m/m\n")

    cols = [(3.0, 2.5, 900.0), (6.0, 2.5, 1400.0), (9.0, 2.5, 900.0), (3.0, 7.5, 1100.0), (6.0, 7.5, 1700.0), (9.0, 7.5, 1100.0)]
    s2 = MatFoundationSolver(length=12.0, width=10.0, thickness=3.0, nx=24, ny=20, E_concrete=30e6, k_s=ks)
    for x, y, P in cols:
        s2.add_column_load(x, y, P)
    r2 = s2.solve()
    P_tot = sum(P for _, _, P in cols)
    A = 120.0
    xg = sum(P * x for x, _, P in cols) / P_tot
    yg = sum(P * y for _, y, P in cols) / P_tot
    Iy, Ix = 10.0 * 12.0 ** 3 / 12, 12.0 * 10.0 ** 3 / 12
    w0 = P_tot / (ks * A)
    thy = P_tot * (xg - 6.0) / (ks * Iy)
    thx = P_tot * (yg - 5.0) / (ks * Ix)
    w_rigid = w0 + thy * (r2.nodes_xy[:, 0] - 6.0) + thx * (r2.nodes_xy[:, 1] - 5.0)
    print(f"2) Losa casi rígida (h = 3 m), ΣP = {P_tot:.0f} kN, resultante en ({xg:.3f}, {yg:.3f}) m:")
    print(f"   sólido rígido sobre muelles: w0 = ΣP/(k_s·A) = {w0 * 1000:.3f} mm, giros {thy:.2e} y {thx:.2e} rad")
    print(f"   paquete: w medio {r2.w.mean() * 1000:.3f} mm; diferencia máxima con el plano rígido "
          f"{np.abs(r2.w - w_rigid).max() * 1000:.3f} mm ({np.abs(r2.w - w_rigid).max() / w0 * 100:.1f} % de w0)\n")

    s3 = MatFoundationSolver(length=12.0, width=10.0, thickness=0.7, nx=24, ny=20, E_concrete=30e6, k_s=ks)
    q_sw = 0.7 * 25.0
    s3.add_uniform_pressure(q_sw)
    for x, y, P in cols:
        s3.add_column_load(x, y, P, name=f"P{x:.0f}-{y:.1f}")
    r3 = s3.solve()
    R = float(np.sum(ks * tributary_areas(s3) * r3.w * (r3.w > 0)))
    print(f"3) Losa 12 × 10 × 0,7 m con peso propio {q_sw} kPa y los 6 pilares:")
    print(f"   Σ reacciones de muelles = {R:.1f} kN; ΣP + q·A = {P_tot + q_sw * A:.1f} kN "
          f"(cierre {(R / (P_tot + q_sw * A) - 1) * 100:+.3f} %)")
    for x, y, P in cols:
        n = s3.node_at(x, y)
        print(f"   pilar ({x:4.1f}, {y:3.1f}) P = {P:5.0f} kN: asiento {r3.w[n] * 1000:5.2f} mm, presión {r3.q_soil[n]:6.1f} kPa")
    print(f"   asiento diferencial {r3.differential_settlement_mm:.2f} mm; M_xx máx {r3.M_xx.max():.0f} y mín "
          f"{r3.M_xx.min():.0f} kN·m/m; {r3.iterations} iteración(es), despegue en {len(r3.uplift_nodes)} nudos\n")

    s4 = MatFoundationSolver(length=12.0, width=10.0, thickness=0.7, nx=24, ny=20, E_concrete=30e6, k_s=ks)
    s4.add_column_load(6.0, 5.0, 3000.0)
    s4.add_column_load(0.5, 0.5, -900.0)
    r4 = s4.solve(allow_uplift=True)
    act = ~np.isin(np.arange(s4.n_nodes), r4.uplift_nodes)
    R4 = float(np.sum(ks * tributary_areas(s4) * r4.w * act))
    print(f"4) Pilar central de 3000 kN y tracción de 900 kN en la esquina (0,5; 0,5):")
    print(f"   {len(r4.uplift_nodes)} nudos despegados tras {r4.iterations} iteraciones (convergido: {r4.converged}); "
          f"Σ reacciones = {R4:.1f} kN frente a ΣP = 2100 kN; w en la esquina traccionada {r4.w[s4.node_at(0.5, 0.5)] * 1000:.2f} mm")

    OUT.mkdir(parents=True, exist_ok=True)
    pj = export_mat_to_json(s3, r3, str(OUT / "losa_12x10.json"))
    ps = export_mat_to_safe(s3, str(OUT / "losa_12x10.s2k"), fck_MPa=30.0)
    print(f"\nExportado: {Path(pj).name} ({Path(pj).stat().st_size / 1024:.0f} kB) y {Path(ps).name} "
          f"({sum(1 for _ in open(ps, encoding='utf-8'))} líneas) en {OUT.name}/")
    print("Límites: cargas de pilar en el nudo más cercano (dependen de la malla), k_s único, sin interacción entre "
          "muelles; el .s2k es un punto de partida (no se ha abierto en SAFE desde este paquete) y su etiqueta de "
          "material es «C<fck>/37» sea cual sea la clase.")


if __name__ == "__main__":
    main()
