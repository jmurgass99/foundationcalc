"""
Verificación frente al hundimiento por flotación / uplift (idea #11).

Cuando el nivel freático sube por encima de la base de una losa o tanque,
existe un empuje hidrostático que puede levantar la estructura. Verifica:

    FS_uplift = W_estabilizador / U_hidrostatico  >= FS_min

con FS_min según código:
- EU (EC 7 §10.2): UPL combination, 1.0 (con γ-factors)
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


_FS_REQ = {
    "USA": 1.5, "ASCE": 1.5, "EU": 1.10, "EUROCODE": 1.10,
    "NSR": 1.5, "CO": 1.5, "AS": 1.5, "AU": 1.5, "SG": 1.10, "SS": 1.10,
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
