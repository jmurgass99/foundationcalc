"""
Verificación frente al hundimiento por flotación / uplift (idea #11).

Cuando el nivel freático sube por encima de la base de una losa o tanque,
existe un empuje hidrostático que puede levantar la estructura. Verifica:

    FS_uplift = W_estabilizador / U_hidrostatico  >= FS_min

con FS_min según código:
- EU (EC 7 §2.4.7.4, estado UPL): G_dst,d ≤ G_stb,d con γ_G;stb = 0,9 y
  γ_G;dst ≥ 1,0, es decir W/U ≥ 1/0,9 = 1,111 como mínimo (1,0 es el valor
  recomendado que se suele citar, sin contrastar en el original; el anejo
  británico usa 1,1 → 1,222). Hasta la 1.1.0 el módulo pedía 1,10, por debajo
  de ese mínimo. La capacidad de anclajes se suma sin factor parcial.
- USA (ASCE 7-22 §2.3.6): FS = 1.5 (servicio) / 1.0 (LRFD con factores)
- NSR-10: 1.5
- AS 1170.0: 1.5
- SG (BC1): similar EU
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class BuoyancyInput:
    base_area_m2: float
    submerged_depth_m: float     # altura agua sobre base
    structure_weight_kN: float
    backfill_weight_kN: float = 0.0
    anchor_capacity_kN: float = 0.0
    gamma_w_kN_m3: float = 9.81
    code: str = "USA"


@dataclass(frozen=True)
class BuoyancyResult:
    uplift_force_kN: float
    stabilizing_force_kN: float
    factor_of_safety: float
    required_FS: float
    passes: bool
    code: str


# EN 1997-1 UPL: γ_G;dst·U ≤ γ_G;stb·W with γ_G;stb = 0.9 and γ_G;dst ≥ 1.0
_FS_UPL_EC7 = 1.0 / 0.9

_FS_REQ = {
    "USA": 1.5, "ASCE": 1.5, "EU": _FS_UPL_EC7, "EUROCODE": _FS_UPL_EC7,
    "NSR": 1.5, "CO": 1.5, "AS": 1.5, "AU": 1.5, "SG": _FS_UPL_EC7, "SS": _FS_UPL_EC7,
}


def check_buoyancy(inp: BuoyancyInput) -> BuoyancyResult:
    if inp.base_area_m2 <= 0:
        raise ValueError("base_area > 0")
    if inp.submerged_depth_m < 0:
        raise ValueError("submerged_depth >= 0")
    c = inp.code.upper()
    if c not in _FS_REQ:
        raise ValueError(f"Código desconocido: {inp.code}")
    U = inp.gamma_w_kN_m3 * inp.submerged_depth_m * inp.base_area_m2
    W = inp.structure_weight_kN + inp.backfill_weight_kN + inp.anchor_capacity_kN
    fs = (W / U) if U > 0 else float("inf")
    req = _FS_REQ[c]
    return BuoyancyResult(
        uplift_force_kN=U,
        stabilizing_force_kN=W,
        factor_of_safety=fs,
        required_FS=req,
        passes=(fs >= req),
        code=inp.code,
    )


def required_ballast_kN(inp: BuoyancyInput) -> float:
    """Lastre adicional para cumplir FS mínimo."""
    r = check_buoyancy(inp)
    needed = r.required_FS * r.uplift_force_kN - (
        inp.structure_weight_kN + inp.backfill_weight_kN + inp.anchor_capacity_kN
    )
    return max(0.0, needed)
