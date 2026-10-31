"""Tower-crane and mobile-crane foundation checks.

A tower-crane foundation is dominated by:
- Very large overturning moment (often `e > L/6` — partial uplift is expected).
- Wind (especially out-of-service combination 'storm').
- Dynamic / impact effects (manufacturers give γ_dynamic 1.10 - 1.30).

This module bundles all the relevant checks against the manufacturer's
working-state and out-of-service load cases per Eurocode 7 (GEO + EQU).

Theory: docs/theory/03_shallow_foundations.md §3.2-3.3 (eccentricity) +
        docs/theory/04_eurocode7_examples.md (bearing capacity).
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from ..codes.eurocode7 import (
    DesignApproach,
    LimitState,
    get_partial_factors,
)
from ..core.geometry import Column, RectangularFoundation
from ..core.material import Concrete
from ..core.soil import SoilLayer
from .base_pressure import BasePressureAnalysis, CornerPressures, PressureRegime
from .bearing_capacity import (
    BearingCapacityFormula,
    BearingCapacityResult,
    drained_bearing_capacity,
    undrained_bearing_capacity,
)
from .stability import (
    OverturningCheck,
    SlidingCheck,
    overturning_check,
    sliding_resistance_drained,
    sliding_resistance_undrained,
)


class CraneLoadState(str, Enum):
    """Standard crane load states (FEM 1.001 / EN 13001 / manufacturer manual)."""

    SERVICE = "in_service"             # operating, max load, max moment
    OUT_OF_SERVICE = "out_of_service"  # storm wind, no load on hook, weather-vaning
    ASSEMBLY = "assembly"              # erection / dismantling
    SEISMIC = "seismic"                # if applicable


class CraneLoadCase(BaseModel):
    """A single crane load case at the foundation top (column base).

    Sign convention follows the rest of the library: fz positive downwards,
    mx about X axis, my about Y axis. `vx`, `vy` are horizontal shears at
    the base of the mast.

    Cranes always have axial N positive (compression) plus an overturning
    moment that creates **partial uplift** on the windward side. The library
    detects this automatically via `analysis.base_pressure`.
    """

    state: CraneLoadState
    name: str = ""
    N_kN: float = Field(..., description="Vertical axial load at column base (kN, +down)")
    M_x_kNm: float = Field(0.0, description="Moment about X (kN·m)")
    M_y_kNm: float = Field(0.0, description="Moment about Y (kN·m)")
    V_x_kN: float = Field(0.0, description="Horizontal shear in X (kN)")
    V_y_kN: float = Field(0.0, description="Horizontal shear in Y (kN)")
    torsion_kNm: float = Field(0.0, description="Torsion (informative)")

    is_wind_dominant: bool = Field(
        False,
        description="True for out-of-service / storm — wind action is variable-leading.",
    )
    dynamic_factor: float = Field(
        1.0, ge=1.0, description="Dynamic amplification on hook load (manufacturer)."
    )

    @property
    def M_resultant(self) -> float:
        """Resultant overturning moment (kN·m), used for symmetric round/square pads."""
        return (self.M_x_kNm ** 2 + self.M_y_kNm ** 2) ** 0.5

    @property
    def V_resultant(self) -> float:
        return (self.V_x_kN ** 2 + self.V_y_kN ** 2) ** 0.5


class CraneCheckResult(BaseModel):
    """Full check bundle for one (load case × design approach) combination."""

    load_case: str
    design_approach: str

    # Eccentricity & contact pressures
    e_x: float
    e_y: float
    regime: str
    q_max: float
    q_avg: float
    active_area_m2: float
    uplift: bool

    # Bearing
    bearing_q_Ed: float
    bearing_q_Rd: float
    bearing_utilization: float

    # Sliding
    sliding_H_Ed: float
    sliding_H_Rd: float
    sliding_utilization: float

    # Overturning
    overturning_M_dst: float
    overturning_M_stb: float
    overturning_utilization: float
    middle_third: bool

    # Uplift / floating safety (W_stab / W_uplift)
    uplift_safety_factor: Optional[float] = None

    @property
    def all_ok(self) -> bool:
        return (
            self.bearing_utilization <= 1.0
            and self.sliding_utilization <= 1.0
            and self.overturning_utilization <= 1.0
            and (self.uplift_safety_factor is None or self.uplift_safety_factor >= 1.5)
        )


def crane_foundation_check(
    foundation: RectangularFoundation,
    column: Column,
    load_case: CraneLoadCase,
    soil: SoilLayer,
    concrete: Concrete,
    design_approach: DesignApproach = DesignApproach.DA2,
    drained: bool = True,
    soil_overburden_depth_mm: float = 0.0,
    soil_unit_weight_overburden: float = 18.0,
    delta_factor: float = 1.0,
    bearing_formula: BearingCapacityFormula = BearingCapacityFormula.CHEN_EC7,
) -> CraneCheckResult:
    """Run the complete set of checks for one crane load case.

    Steps:
      1. Build a factored combination using the active Design Approach.
      2. Compute corner pressures with `BasePressureAnalysis` (handles e>L/6).
      3. Compute bearing capacity (effective-area method).
      4. Check sliding at the base.
      5. Check overturning + middle-third.

    Args:
        foundation: the pad (square or rectangular).
        column: pedestal/mast at the centre of the pad.
        load_case: the manufacturer's design state (service / OOS / etc).
        soil: founding-level soil layer.
        concrete: concrete used (for self-weight γ).
        design_approach: EC7 DA selector (default DA-2, the Spanish convention).
        drained: True for sand, False for undrained clay.
        soil_overburden_depth_mm: backfill height above the footing.
        delta_factor: 2/3 for precast pads, 1.0 for cast-in-place.
    """
    pf = get_partial_factors(design_approach, LimitState.GEO)
    gG = pf.actions.gamma_G_unfav
    gQ = pf.actions.gamma_Q_unfav

    # Treat wind-dominant cases with γ_Q on the moment (storm), otherwise γ_G on N.
    if load_case.is_wind_dominant:
        N_d = gG * load_case.N_kN
        M_x_d = gQ * load_case.M_x_kNm * load_case.dynamic_factor
        M_y_d = gQ * load_case.M_y_kNm * load_case.dynamic_factor
        V_x_d = gQ * load_case.V_x_kN
        V_y_d = gQ * load_case.V_y_kN
    else:
        N_d = gG * load_case.N_kN
        M_x_d = gG * load_case.M_x_kNm * load_case.dynamic_factor
        M_y_d = gG * load_case.M_y_kNm * load_case.dynamic_factor
        V_x_d = gG * load_case.V_x_kN
        V_y_d = gG * load_case.V_y_kN

    # Footing self-weight (always permanent — γ_G,fav for stabilising in OOS)
    W_footing = foundation.area * foundation.thickness_m * concrete.unit_weight
    W_soil = (
        foundation.area
        * (soil_overburden_depth_mm / 1000.0)
        * soil_unit_weight_overburden
    )
    W_total_char = W_footing + W_soil
    gG_fav = pf.actions.gamma_G_fav
    W_d_fav = gG_fav * W_total_char  # use favourable for sliding / overturning
    W_d_unfav = gG * W_total_char    # use unfavourable for bearing

    # 1. Contact pressures via BasePressureAnalysis (handles e>L/6) -----------
    # Build a combination with FACTORED crane loads + FACTORED self-weight,
    # then bypass BasePressureAnalysis's auto self-weight to avoid double-counting.
    from ..core.loading import CombinationEntry, LoadCombination, LoadType, PointLoad

    synthetic = LoadCombination(
        name=f"crane_{load_case.state.value}",
        entries=[
            CombinationEntry(
                load=PointLoad(
                    name="crane",
                    fz=N_d,
                    mx=M_x_d,
                    my=M_y_d,
                    vx=V_x_d,
                    vy=V_y_d,
                ),
                factor=1.0,
            ),
            CombinationEntry(
                load=PointLoad(
                    name="self_weight_factored",
                    fz=W_d_unfav,
                    load_type=LoadType.PERMANENT,
                ),
                factor=1.0,
            ),
        ],
    )
    bpa = BasePressureAnalysis(foundation, column)
    press: CornerPressures = bpa.calculate_pressures(
        synthetic,
        include_self_weight=False,  # already in the combination
    )
    uplift = press.regime == PressureRegime.OUTSIDE_CORE or press.q_min <= 0.01

    # Used downstream by bearing & overturning
    N_for_pressure = synthetic.total_fz
    e_x = press.e_x
    e_y = press.e_y

    # 2. Bearing capacity --------------------------------------------------
    L_eff, B_eff = foundation.effective_dimensions(e_x, e_y)
    if drained:
        bc: BearingCapacityResult = drained_bearing_capacity(
            foundation=foundation,
            soil=soil,
            e_x=e_x,
            e_y=e_y,
            H_load=(V_x_d ** 2 + V_y_d ** 2) ** 0.5,
            V_load=N_for_pressure,
            gamma_Rv=pf.resistance.gamma_Rv,
            gamma_phi=pf.soil.gamma_phi,
            gamma_c=pf.soil.gamma_c,
            gamma_gamma=pf.soil.gamma_gamma,
            formula=bearing_formula,
        )
    else:
        bc = undrained_bearing_capacity(
            foundation=foundation,
            soil=soil,
            e_x=e_x,
            e_y=e_y,
            H_load=(V_x_d ** 2 + V_y_d ** 2) ** 0.5,
            gamma_Rv=pf.resistance.gamma_Rv,
            gamma_cu=pf.soil.gamma_cu,
        )

    q_Ed = N_for_pressure / max(bc.A_eff, 1e-6)
    q_Rd = bc.q_ult / pf.resistance.gamma_Rv
    bearing_util = q_Ed / max(q_Rd, 1e-6)

    # 3. Sliding ----------------------------------------------------------
    H_total = (V_x_d ** 2 + V_y_d ** 2) ** 0.5
    if drained:
        sliding: SlidingCheck = sliding_resistance_drained(
            N_Ed=W_d_fav + load_case.N_kN * pf.actions.gamma_G_fav,
            soil=soil,
            A_eff=bc.A_eff,
            H_Ed=H_total,
            delta_factor=delta_factor,
            gamma_phi=pf.soil.gamma_phi,
            gamma_c=pf.soil.gamma_c,
            gamma_Rh=pf.resistance.gamma_Rh,
        )
    else:
        sliding = sliding_resistance_undrained(
            N_Ed=W_d_fav + load_case.N_kN * pf.actions.gamma_G_fav,
            soil=soil,
            A_eff=bc.A_eff,
            H_Ed=H_total,
            gamma_cu=pf.soil.gamma_cu,
            gamma_Rh=pf.resistance.gamma_Rh,
        )

    # 4. Overturning (about the worst edge — use resultant moment) --------
    B = min(foundation.length_m, foundation.width_m)
    M_dst = (M_x_d ** 2 + M_y_d ** 2) ** 0.5
    # Add the moment from horizontal shear at footing-base level
    M_dst += H_total * foundation.thickness_m
    # Stabilising moment = W_d_fav · B/2
    M_stb = (W_d_fav + pf.actions.gamma_G_fav * load_case.N_kN) * (B / 2.0)
    overturn: OverturningCheck = overturning_check(
        M_dst_d=M_dst,
        M_stb_d=M_stb,
        V_d=N_for_pressure,
        B=B,
    )

    return CraneCheckResult(
        load_case=load_case.state.value,
        design_approach=design_approach.value,
        e_x=round(e_x, 4),
        e_y=round(e_y, 4),
        regime=press.regime.value,
        q_max=press.q_max,
        q_avg=press.q_avg,
        active_area_m2=press.active_area_m2,
        uplift=uplift,
        bearing_q_Ed=q_Ed,
        bearing_q_Rd=q_Rd,
        bearing_utilization=bearing_util,
        sliding_H_Ed=H_total,
        sliding_H_Rd=sliding.H_Rd,
        sliding_utilization=sliding.utilization,
        overturning_M_dst=M_dst,
        overturning_M_stb=M_stb,
        overturning_utilization=overturn.utilization,
        middle_third=overturn.middle_third,
    )


def design_envelope(
    foundation: RectangularFoundation,
    column: Column,
    load_cases: List[CraneLoadCase],
    soil: SoilLayer,
    concrete: Concrete,
    design_approaches: Optional[List[DesignApproach]] = None,
    **kwargs,
) -> List[CraneCheckResult]:
    """Run every (load case × design approach) combination and return the list.

    Use the maximum utilization across all results as the governing case.
    """
    if design_approaches is None:
        design_approaches = [
            DesignApproach.DA1_C1,
            DesignApproach.DA1_C2,
            DesignApproach.DA2,
            DesignApproach.DA3,
        ]
    results = []
    for lc in load_cases:
        for da in design_approaches:
            results.append(
                crane_foundation_check(
                    foundation=foundation,
                    column=column,
                    load_case=lc,
                    soil=soil,
                    concrete=concrete,
                    design_approach=da,
                    **kwargs,
                )
            )
    return results
