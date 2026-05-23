"""Bridge between FoundationDesignJm and DynamicsJm.

Closes the loop on roadmap item #1 (SSI): we already compute
`FoundationImpedance` (Gazetas 1991) here, and `DynamicsJm` provides the
dynamic SDOF/MDOF solvers, the FEMA P-58 loss models (ported from EaRL)
and the control devices (base isolators, TMDs).

This module:

1. **Converts** our 6-DOF impedance into the springs / damping that
   `DynamicsJm` expects at the base of a structure.
2. **Modifies the natural period** of a fixed-base SDOF to account for
   the foundation flexibility:

         (T_SSI / T_fix)^2  =  1 + k_struct/K_h + k_struct·h²/K_r

   (Veletsos & Meek 1974). The damping is similarly elongated.
3. **Runs the full pipeline**:

        CPT  →  SoilProfile (FoundationDesignJm)
             →  FoundationImpedance (FoundationDesignJm)
             →  SSI-modified SDOF + isolator (DynamicsJm)
             →  IDR from dynamic response (DynamicsJm)
             →  FEMA P-58 repair cost (DynamicsJm.risk)

`DynamicsJm` is an **optional** dependency. If it is not installed the
helpers raise `ImportError` with a clear message.

Theory: docs/theory/19_ssi_bridge.md  +  Veletsos & Meek (1974), FEMA
P-58 (2018), Gazetas (1991).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

from ..analysis.cpt import CPTProfile
from ..core.geometry import RectangularFoundation
from ..dynamics.foundation_impedance import (
    FoundationImpedance,
    rectangular_footing_impedance,
)


# ---------------------------------------------------------------------------
# Optional dependency detection
# ---------------------------------------------------------------------------

try:                                                           # pragma: no cover
    from dynamicsjm.risk.loss_model import (                  # type: ignore
        EarthquakeRiskAnalyzer,
        FEMAP58LossModel,
    )
    from dynamicsjm.control.base_isolation import BilinearIsolator  # type: ignore  # noqa: F401
    from dynamicsjm.solvers.direct import DirectSolver         # type: ignore
    from dynamicsjm.systems.sdof import SDOFSystem             # type: ignore
    DYNAMICSJM_AVAILABLE = True
except ImportError:
    DYNAMICSJM_AVAILABLE = False


def _require_dynamicsjm() -> None:
    if not DYNAMICSJM_AVAILABLE:
        raise ImportError(
            "DynamicsJm is required for this pipeline. Install / make it "
            "importable (see the DynamicsJm folder under STRUCTURAL/APIS/)."
        )


# ---------------------------------------------------------------------------
# Spring conversion + SSI period
# ---------------------------------------------------------------------------

def impedance_to_springs(imp: FoundationImpedance) -> Dict[str, Dict[str, float]]:
    """Convert a `FoundationImpedance` into a dict ready to feed to DynamicsJm.

    The output structure is

    .. code-block:: python

        {
            "vertical":     {"K_static": ..., "K_dyn": ..., "C_dyn": ...},
            "horizontal_x": {...},
            "horizontal_y": {...},
            "rocking_x":    {...},
            "rocking_y":    {...},
            "torsion":      {...},
        }

    which matches the conventions of the SDOF / MDOF systems of
    DynamicsJm v5.5+ when extended with base springs.
    """
    out: Dict[str, Dict[str, float]] = {}
    for name in ("vertical", "horizontal_x", "horizontal_y",
                 "rocking_x", "rocking_y", "torsion"):
        d = getattr(imp, name, None)
        if d is None:
            continue
        out[name] = {
            "K_static": d.K_static,
            "K_dyn":    d.K_dyn,
            "C_dyn":    d.C_dyn,
        }
    return out


@dataclass
class SSIResponse:
    """SSI-modified dynamic properties for a SDOF building."""

    T_fixed: float       # fixed-base natural period (s)
    T_ssi: float         # SSI-modified period (s)
    period_elongation: float
    zeta_fixed: float    # fixed-base damping ratio
    zeta_ssi: float      # SSI damping ratio (includes radiation damping)
    K_h_kN_m: float
    K_r_kNm_rad: float
    m_struct_kg: float
    h_struct_m: float


def ssi_modified_period(
    T_fixed_s: float,
    m_struct_kg: float,
    h_struct_m: float,
    impedance: FoundationImpedance,
    zeta_fixed: float = 0.05,
) -> SSIResponse:
    """Veletsos & Meek (1974) SSI period elongation for a SDOF on flexible base.

    .. math::

        \\left(\\frac{T_{ssi}}{T_{fix}}\\right)^2 = 1
            + \\frac{k_{struct}}{K_h}
            + \\frac{k_{struct} \\, h^2}{K_r}

    The SSI damping is the weighted average of structural damping and
    radiation damping at the foundation, approximated by:

        ζ_ssi = (T_fix/T_ssi)³ · ζ_fixed + ζ_radiation

    with ζ_radiation derived from the horizontal + rocking damping
    coefficients.

    Args:
        T_fixed_s:    fixed-base natural period of the building (s).
        m_struct_kg:  modal mass of the building (kg).
        h_struct_m:   effective height (m).
        impedance:    output of `rectangular_footing_impedance`.
        zeta_fixed:   structural damping ratio (default 0.05).
    """
    if impedance.horizontal_x is None or impedance.rocking_y is None:
        raise ValueError("Impedance must include horizontal and rocking DOFs.")
    K_h = impedance.horizontal_x.K_static * 1000.0   # kN/m → N/m
    K_r = impedance.rocking_y.K_static * 1000.0      # kN·m → N·m
    omega_fixed = 2.0 * math.pi / max(T_fixed_s, 1e-6)
    k_struct = m_struct_kg * omega_fixed ** 2        # N/m

    ratio_sq = 1.0 + k_struct / K_h + k_struct * h_struct_m ** 2 / K_r
    T_ssi = T_fixed_s * math.sqrt(ratio_sq)

    # Radiation damping contribution (simplified)
    if impedance.horizontal_x and impedance.rocking_y:
        zeta_rad = 0.5 * (
            impedance.horizontal_x.c_dyn
            + impedance.rocking_y.c_dyn
        )
        zeta_rad = min(zeta_rad, 0.3)
    else:
        zeta_rad = 0.0
    zeta_ssi = (T_fixed_s / T_ssi) ** 3 * zeta_fixed + zeta_rad

    return SSIResponse(
        T_fixed=T_fixed_s, T_ssi=T_ssi,
        period_elongation=T_ssi / T_fixed_s,
        zeta_fixed=zeta_fixed, zeta_ssi=zeta_ssi,
        K_h_kN_m=impedance.horizontal_x.K_static,
        K_r_kNm_rad=impedance.rocking_y.K_static,
        m_struct_kg=m_struct_kg,
        h_struct_m=h_struct_m,
    )


# ---------------------------------------------------------------------------
# End-to-end pipeline
# ---------------------------------------------------------------------------

@dataclass
class SeismicLossPipelineResult:
    """Output bundle of the full CPT → SSI → dynamic → loss pipeline."""

    impedance: FoundationImpedance
    ssi_fixed: SSIResponse
    ssi_isolated: Optional[SSIResponse]
    peak_idr_fixed: float
    peak_idr_isolated: Optional[float]
    loss_fixed_USD: float
    loss_isolated_USD: Optional[float]
    loss_reduction_pct: Optional[float]


def cpt_to_seismic_loss_pipeline(
    cpt: CPTProfile,
    foundation: RectangularFoundation,
    building_mass_kg: float,
    building_height_m: float,
    building_T_fixed_s: float,
    ground_motion_t_s: np.ndarray,
    ground_motion_a_g: np.ndarray,
    isolator: Optional[object] = None,
    loss_models: Optional[list] = None,
) -> SeismicLossPipelineResult:
    """Full pipeline: CPT → SSI springs → dynamic → IDR → FEMA P-58 loss.

    Two scenarios are run inside:

    1. **Fixed base** of the structure on the SSI-flexible foundation.
    2. **Base-isolated** variant if `isolator` is provided (typically
       a `BilinearIsolator` from `dynamicsjm.control.base_isolation`).

    For each scenario the peak inter-story drift ratio is computed and
    fed to the EaRL/FEMA P-58 loss model — the SM1 default is used if
    no other model list is passed.

    The pipeline requires DynamicsJm to be installed.
    """
    _require_dynamicsjm()

    # 1) Estimate G_max from CPT (use a quick correlation: G_max ≈ 50·q_c MPa
    #    for clean sands, see Robertson 2009). We average q_t over the layers
    #    inside the influence zone 2B below the footing.
    B = foundation.width_m
    z_top = foundation.embedment_depth / 1000.0   # mm -> m
    z_bot = z_top + 2.0 * B
    qts = [r.q_t_MPa for r in cpt.readings if z_top <= r.depth <= z_bot]
    qt_avg = float(np.mean(qts)) if qts else 5.0
    G_max_MPa = 50.0 * qt_avg
    nu = 0.30

    # 2) Foundation impedance from the averaged G_max
    impedance = rectangular_footing_impedance(
        B_m=foundation.width_m, L_m=foundation.length_m,
        G_MPa=G_max_MPa, nu=nu, frequency_Hz=1.0 / building_T_fixed_s,
    )

    # 3) SSI-modified period (fixed-base structure on flexible foundation)
    ssi_fix = ssi_modified_period(
        T_fixed_s=building_T_fixed_s,
        m_struct_kg=building_mass_kg,
        h_struct_m=building_height_m,
        impedance=impedance,
    )

    # 4) Dynamic analysis — fixed-base structure
    omega_ssi = 2.0 * math.pi / ssi_fix.T_ssi
    k_eff = building_mass_kg * omega_ssi ** 2
    system_fix = SDOFSystem(
        mass=building_mass_kg, stiffness=k_eff,
        damping_ratio=ssi_fix.zeta_ssi,
    )
    # DynamicsJm Newmark expects a force history F(t) = -m · a_g(t)
    F_history = -building_mass_kg * np.asarray(ground_motion_a_g)
    u_fix, _v_fix, _a_fix = DirectSolver.newmark_beta(
        system_fix, np.asarray(ground_motion_t_s), F_history,
    )
    peak_disp_fix = float(np.max(np.abs(u_fix)))
    peak_idr_fix = peak_disp_fix / building_height_m

    # 5) Loss assessment (default SM1)
    if loss_models is None:
        loss_models = [FEMAP58LossModel.structural_member_1()]
    analyzer = EarthquakeRiskAnalyzer(loss_models)
    edp_data_fix = {m.name: peak_idr_fix for m in loss_models}
    loss_fix, _ = analyzer.estimate_scenario_loss(edp_data_fix)

    # 6) Isolated scenario — if user provides isolator
    peak_idr_iso = None
    loss_iso = None
    ssi_iso = None
    if isolator is not None:
        # Estimate the iso-modified period by combining the isolator and
        # structural stiffness in series:
        k_iso = isolator.k1
        k_combined = (k_eff * k_iso) / (k_eff + k_iso)
        omega_iso = math.sqrt(k_combined / building_mass_kg)
        T_iso = 2.0 * math.pi / omega_iso
        ssi_iso = SSIResponse(
            T_fixed=ssi_fix.T_fixed, T_ssi=T_iso,
            period_elongation=T_iso / ssi_fix.T_fixed,
            zeta_fixed=ssi_fix.zeta_fixed,
            zeta_ssi=max(ssi_fix.zeta_ssi, isolator.damping_ratio),
            K_h_kN_m=impedance.horizontal_x.K_static,
            K_r_kNm_rad=impedance.rocking_y.K_static,
            m_struct_kg=building_mass_kg,
            h_struct_m=building_height_m,
        )
        system_iso = SDOFSystem(
            mass=building_mass_kg, stiffness=k_combined,
            damping_ratio=max(ssi_fix.zeta_ssi, isolator.damping_ratio),
        )
        u_iso, _v_iso, _a_iso = DirectSolver.newmark_beta(
            system_iso, np.asarray(ground_motion_t_s), F_history,
        )
        # The displacement above is the TOTAL system displacement, almost
        # entirely concentrated on the isolator. The structure's drift
        # (the EDP that FEMA P-58 uses) is the much smaller relative
        # deformation of the superstructure:
        #     u_struct ≈ u_total · (k_iso / k_struct)
        # which follows from the series-spring force balance.
        peak_disp_total = float(np.max(np.abs(u_iso)))
        u_struct = peak_disp_total * (k_iso / k_eff)
        peak_idr_iso = u_struct / building_height_m
        edp_data_iso = {m.name: peak_idr_iso for m in loss_models}
        loss_iso, _ = analyzer.estimate_scenario_loss(edp_data_iso)

    loss_reduction_pct = (
        (loss_fix - loss_iso) / loss_fix * 100.0
        if loss_iso is not None and loss_fix > 0
        else None
    )

    return SeismicLossPipelineResult(
        impedance=impedance,
        ssi_fixed=ssi_fix,
        ssi_isolated=ssi_iso,
        peak_idr_fixed=peak_idr_fix,
        peak_idr_isolated=peak_idr_iso,
        loss_fixed_USD=loss_fix,
        loss_isolated_USD=loss_iso,
        loss_reduction_pct=loss_reduction_pct,
    )


__all__ = [
    "DYNAMICSJM_AVAILABLE",
    "SSIResponse",
    "SeismicLossPipelineResult",
    "impedance_to_springs",
    "ssi_modified_period",
    "cpt_to_seismic_loss_pipeline",
]
