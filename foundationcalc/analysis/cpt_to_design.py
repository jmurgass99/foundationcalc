"""End-to-end footing design directly from a CPT log.

This is the integration module: feed a `CPTProfile` plus a candidate
`RectangularFoundation` and a target net pressure, and the pipeline
returns:

- A derived `SoilProfile` (one layer per CPT segment with φ, c_u, E
  back-figured from the cone resistance).
- Multi-layer bearing capacity (Meyerhof-Hanna 1978 when applicable).
- Failure-mode classification (Vesic I_r) at the founding plane.
- Total settlement (immediate + consolidation) under the centre.
- ULS / SLS verdicts using the chosen Design Approach.

This module ties together `cpt`, `bearing_capacity`, `failure_mode`,
`multi_layer_bc` and `footing_settlement`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel

from ..codes.eurocode7 import DesignApproach, LimitState, get_partial_factors
from ..core.geometry import RectangularFoundation
from ..core.soil import SoilLayer, SoilProfile, SoilType
from .cpt import CPTProfile, SBTZone
from .failure_mode import classify_failure_mode, FailureModeResult
from .footing_settlement import (
    FootingSettlementResult,
    total_footing_settlement,
)
from .multi_layer_bc import MultiLayerBCResult, multi_layer_bearing_capacity


def _estrato_txt(s) -> str:
    z0, z1 = getattr(s, "z_top", getattr(s, "z_top_m", "?")), getattr(s, "z_bot", getattr(s, "z_bot_m", "?"))
    return f"estrato {z0}-{z1} m"


def _cu_del_estrato(s) -> float:
    """c_u del estrato por PRESENCIA (B48, §8.29).

    Antes: ``s.c_u_kPa or 40.0``. Un c_u = 0.0 MEDIDO --que el esquema admite,
    ge=0-- se convertia en 40 kPa inventados. Medido: la misma zapata pasaba de
    bearing_ok=False (q_Rd 6.43) a True (q_Rd 32.56). Un 0.0 medido es un dato.
    """
    cu = getattr(s, "c_u_kPa", None)
    if cu is None:
        raise ValueError(
            f"{_estrato_txt(s)}: el correlador CPT no dio c_u para un estrato "
            "cohesivo; no se asume ninguno (antes: 40 kPa)"
        )
    return float(cu)


def _E_del_estrato(s) -> float:
    """E del estrato, o un error que nombra el estrato (B48, §8.29).

    Antes: ``s.E_MPa or 30.0`` (arena) y ``or 5.0`` (arcilla). El correlador
    devuelve E = 0 cuando q_t <= sigma'_v0, FUERA del rango de Robertson (2009),
    y ese 0 se convertia en un modulo inventado que ademas afecta a q_Rd: con
    E -> 0 el factor zeta_q de Vesic cae de 1.0 a 0.43. Medido: q_Rd 51.82 ->
    22.5, bearing_ok True -> False.

    No se guarda None porque seis consumidores (informe PDF, dashboard,
    escritorio, optimizador) hacen ``"OK" if res.bearing_ok else "FAIL"`` y un
    None se imprimiria como FALLA: un «no calculado» disfrazado de «no cumple».
    Se niega a construir el perfil, con el estrato nombrado.
    """
    E = getattr(s, "E_MPa", None)
    if E is None or not (float(E) > 0.0):
        raise ValueError(
            f"{_estrato_txt(s)}: modulo E correlado = {E!r} (q_t <= sigma'_v0, fuera "
            "del rango de Robertson 2009). No se asume ninguno (antes: 30 MPa en "
            "arena, 5 MPa en arcilla)"
        )
    return float(E)


def soil_profile_from_cpt(
    cpt: CPTProfile, n_layers: int = 5,
) -> SoilProfile:
    """Build a SoilProfile from a CPT log via stratification.

    Each Robertson SBT zone is mapped to a SoilType + φ' or c_u + E.
    """
    summaries = cpt.stratify(n_layers=n_layers)
    soil_layers: List[SoilLayer] = []
    for i, s in enumerate(summaries):
        # El primer estrato llega hasta la superficie: SoilProfile empieza en
        # z = 0 y la primera lectura del CPT no. DEFECTO CORREGIDO (1.1.0):
        # antes el primer estrato medía z_bot − z_top y todos los contactos
        # del perfil subían tanto como la profundidad de la primera lectura.
        z_top = 0.0 if i == 0 else s.z_top
        thickness = max(s.z_bot - z_top, 0.1)
        if s.sbt_zone in (SBTZone.SAND, SBTZone.SAND_MIX, SBTZone.DENSE_SAND_GRAVEL):
            soil_layers.append(SoilLayer(
                name=f"{s.sbt_zone.name.lower()}_{round(s.z_top, 1)}m",
                thickness=thickness,
                soil_type=SoilType.COHESIONLESS,
                friction_angle=s.phi_deg or 32.0,
                cohesion=0.0,
                unit_weight=cpt.gamma_above_wt_kN_m3,
                saturated_unit_weight=cpt.gamma_below_wt_kN_m3,
                youngs_modulus=_E_del_estrato(s),
                cone_resistance_qc=s.q_t_avg_MPa,
            ))
        else:
            cu = _cu_del_estrato(s)
            soil_layers.append(SoilLayer(
                name=f"{s.sbt_zone.name.lower()}_{round(s.z_top, 1)}m",
                thickness=thickness,
                soil_type=SoilType.COHESIVE,
                friction_angle=0.0,
                cohesion=0.0,
                undrained_shear_strength=cu,
                unit_weight=cpt.gamma_above_wt_kN_m3,
                saturated_unit_weight=cpt.gamma_below_wt_kN_m3,
                youngs_modulus=_E_del_estrato(s),
                cone_resistance_qc=s.q_t_avg_MPa,
            ))
    return SoilProfile(
        layers=soil_layers,
        water_table_depth=cpt.water_table_depth_m,
        gamma_w=cpt.gamma_w_kN_m3,
    )


@dataclass
class FootingDesignFromCPT:
    profile: SoilProfile
    bearing: MultiLayerBCResult
    failure_mode: FailureModeResult
    settlement: FootingSettlementResult
    q_applied_kPa: float
    q_Rd_kPa: float
    bearing_utilization: float
    bearing_ok: bool
    settlement_limit_mm: float
    settlement_ok: bool
    design_approach: str


def design_footing_from_cpt(
    cpt: CPTProfile,
    foundation: RectangularFoundation,
    founding_depth_m: float,
    q_applied_kPa: float,
    design_approach: DesignApproach = DesignApproach.DA2,
    n_strata: int = 5,
    settlement_limit_mm: float = 50.0,
    sub_layer_thickness_m: float = 0.5,
) -> FootingDesignFromCPT:
    """Complete pipeline: CPT → design verdict for a candidate footing.

    Args:
        cpt:                CPT log.
        foundation:         candidate footing geometry.
        founding_depth_m:   depth of the base of the footing.
        q_applied_kPa:      total contact pressure (ULS for bearing,
                            SLS-quasi-permanent or characteristic for
                            settlement — pass the appropriate value).
        design_approach:    EC7 DA selector for γ_Rv.
        settlement_limit_mm: SLS criterion (EC7 Annex H typical = 50 mm).

    Returns:
        FootingDesignFromCPT with bearing capacity, failure mode,
        settlement and pass/fail status.
    """
    # 1) Derived soil profile
    profile = soil_profile_from_cpt(cpt, n_layers=n_strata)

    # 2) Multi-layer bearing capacity
    bc = multi_layer_bearing_capacity(foundation, profile, founding_depth_m)

    # 3) Failure mode classification at founding layer
    found_layer = profile.layer_at(founding_depth_m + 1e-6)
    q_overburden = profile.effective_stress_at(founding_depth_m)
    fm = classify_failure_mode(
        E_kPa=(found_layer.youngs_modulus or 30.0) * 1000.0,
        nu=found_layer.poisson_ratio or 0.3,
        c_prime_kPa=found_layer.cohesion,
        phi_deg=found_layer.friction_angle,
        q_prime_kPa=q_overburden,
        B_m=foundation.width_m,
        L_m=foundation.length_m,
        Nq=15.0,   # conservative default; the actual Nq is inside BC
    )

    # 4) Settlement under the centre
    settle = total_footing_settlement(
        foundation, profile, founding_depth_m, q_applied_kPa,
        sub_layer_thickness_m=sub_layer_thickness_m,
    )

    # 5) Pass/fail
    pf = get_partial_factors(design_approach, LimitState.GEO)
    q_Rd = bc.q_ult_kPa / pf.resistance.gamma_Rv * fm.zeta_q  # apply Vesic reduction
    bearing_util = q_applied_kPa / max(q_Rd, 1e-6)
    bearing_ok = bearing_util <= 1.0
    settlement_ok = settle.s_total_mm <= settlement_limit_mm

    return FootingDesignFromCPT(
        profile=profile,
        bearing=bc,
        failure_mode=fm,
        settlement=settle,
        q_applied_kPa=q_applied_kPa,
        q_Rd_kPa=q_Rd,
        bearing_utilization=bearing_util,
        bearing_ok=bearing_ok,
        settlement_limit_mm=settlement_limit_mm,
        settlement_ok=settlement_ok,
        design_approach=design_approach.value,
    )


__all__ = [
    "FootingDesignFromCPT",
    "soil_profile_from_cpt",
    "design_footing_from_cpt",
]
