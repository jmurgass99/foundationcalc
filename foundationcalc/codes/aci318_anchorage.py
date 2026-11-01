"""ACI 318-19 Chapter 17 — Anchorage to concrete (cast-in headed anchors).

Implements the principal failure modes for an individual anchor or simple
group under tension and shear:

- Tension: steel (17.6.1), concrete breakout (17.6.2), pullout (17.6.3),
  side-face blowout (17.6.4).
- Shear: steel (17.7.1), concrete breakout (17.7.2), pryout (17.7.3).
- Combined tension + shear interaction (17.8.3): (Nu/phiNn)^5/3 + (Vu/phiVn)^5/3 ≤ 1.

Units: N, mm, MPa (consistent SI).
phi_steel = 0.75 in tension and 0.65 in shear (ductile, Table 17.5.3),
phi_concrete = 0.65 for every concrete mode (Table 17.5.3 differentiates by
anchor type and Condition A/B; not differentiated here).

Theory: docs/theory/aci318_anchorage.md (planned).
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

PHI_STEEL = 0.75        # ductile steel element, tension (ACI 318-19 Table 17.5.3)
PHI_STEEL_SHEAR = 0.65  # ductile steel element, shear (ACI 318-19 Table 17.5.3)
PHI_CONCRETE = 0.65


class AnchorCondition(str, Enum):
    """ACI 318 17.6.2.5: presence of supplementary reinforcement."""

    A = "A"  # with supplementary reinforcement: psi_c,N = 1.25 (uncracked)
    B = "B"  # without:                          psi_c,N = 1.0 cracked, 1.4 uncracked


class AnchorTensionResult(BaseModel):
    """Tensile capacity components and governing limit state."""

    Nsa: float = Field(..., description="Steel strength (N), §17.6.1.2")
    Ncb: float = Field(..., description="Concrete breakout (N), §17.6.2.1")
    Npn: float = Field(..., description="Pullout (N), §17.6.3.2 or +inf if Abrg=0")
    Nsb: float = Field(..., description="Side-face blowout (N), or +inf if N/A")
    phi_Nn: float = Field(..., description="Factored design tensile strength (N)")
    governing: str = Field(..., description="steel | breakout | pullout | blowout")
    Nu: float = Field(..., description="Applied factored tension (N)")
    utilization: float = Field(..., description="Nu / phi_Nn")
    ok: bool


class AnchorShearResult(BaseModel):
    """Shear capacity components and governing limit state."""

    Vsa: float = Field(..., description="Steel strength (N), §17.7.1.2")
    Vcb: float = Field(..., description="Concrete breakout (N), §17.7.2.1")
    Vcp: float = Field(..., description="Pryout (N), §17.7.3.1")
    phi_Vn: float
    governing: str
    Vu: float
    utilization: float
    ok: bool


class AnchorInteractionResult(BaseModel):
    interaction: float = Field(..., description="(Nu/phiNn)^5/3 + (Vu/phiVn)^5/3")
    rule: str = Field(..., description="tension_only | shear_only | combined_5/3")
    ok: bool


def tension_capacity(
    *,
    Nu: float,
    Ase_N: float,
    futa: float,
    fc: float,
    hef: float,
    ca1: float,
    Abrg: float = 0.0,
    condition: AnchorCondition = AnchorCondition.B,
    cracked: bool = True,
    n_anchors: int = 1,
) -> AnchorTensionResult:
    """Tension capacity of a cast-in headed anchor per ACI 318-19 §17.6.

    Args:
        Nu: factored tension demand (N).
        Ase_N: effective steel cross-area in tension (mm²).
        futa: ultimate steel stress; min(1.9·fy, 860 MPa).
        fc: concrete f'c (MPa).
        hef: effective embedment (mm).
        ca1: edge distance to nearest free edge (mm).
        Abrg: bearing area of the head (mm²); 0 disables pullout/blowout.
        condition: A (with supplementary reinforcement) or B.
        cracked: True if concrete is cracked in service.
        n_anchors: anchors acting together (group simplified).
    """
    # Steel (17.6.1.2)
    Nsa = n_anchors * Ase_N * futa

    # Breakout (17.6.2): Ncb = (ANc/ANco) · ψ_ed · ψ_c · ψ_cp · Nb
    # kc = 10 for cast-in headed anchors (17.6.2.2.1); cracked/uncracked
    # enters via ψ_c (17.6.2.6).
    kc = 10.0
    Nb = kc * math.sqrt(fc) * hef**1.5
    ANco = 9.0 * hef * hef
    ANc = min(ANco, (1.5 * hef + max(ca1, 0)) * (3.0 * hef))
    psi_ed = 1.0 if ca1 >= 1.5 * hef else 0.7 + 0.3 * ca1 / (1.5 * hef)
    if cracked:
        psi_c = 1.0
    else:
        psi_c = 1.25 if condition == AnchorCondition.A else 1.4
    psi_cp = 1.0
    Ncb = (ANc / ANco) * psi_ed * psi_c * psi_cp * Nb * n_anchors

    # Pullout (17.6.3.2): Npn = ψ_c,P · Np ; Np = 8·Abrg·fc
    psi_cP = 1.0 if cracked else 1.4
    Np = 8.0 * max(Abrg, 0.0) * fc
    Npn = psi_cP * Np * n_anchors if Abrg > 0 else math.inf

    # Side-face blowout (17.6.4): only headed, hef > 2.5·ca1
    if Abrg > 0 and hef > 2.5 * ca1 and ca1 > 0:
        Nsb = 13.0 * ca1 * math.sqrt(Abrg) * math.sqrt(fc) * n_anchors
    else:
        Nsb = math.inf

    Nn_steel = PHI_STEEL * Nsa
    cand_conc = {"breakout": PHI_CONCRETE * Ncb,
                  "pullout":  PHI_CONCRETE * Npn,
                  "blowout":  PHI_CONCRETE * Nsb}
    Nn_conc = min(cand_conc.values())
    phi_Nn = min(Nn_steel, Nn_conc)
    all_candidates = {"steel": Nn_steel, **cand_conc}
    governing = min(all_candidates, key=all_candidates.get)

    util = abs(Nu) / max(phi_Nn, 1e-9)
    return AnchorTensionResult(
        Nsa=Nsa, Ncb=Ncb, Npn=Npn, Nsb=Nsb,
        phi_Nn=phi_Nn, governing=governing,
        Nu=Nu, utilization=util, ok=util <= 1.0,
    )


def shear_capacity(
    *,
    Vu: float,
    Ase_V: float,
    futa: float,
    fc: float,
    hef: float,
    ca1: float,
    da: float,
    le: Optional[float] = None,
    cracked: bool = True,
    n_anchors: int = 1,
) -> AnchorShearResult:
    """Shear capacity of a cast-in headed anchor per ACI 318-19 §17.7.

    Args:
        Vu: factored shear demand (N).
        Ase_V: effective steel cross-area in shear (mm²).
        futa: ultimate steel stress (MPa). See "futa cap" below — unlike
            ``tension_capacity``, this docstring did not even state the cap
            as a precondition until now.
        fc: concrete f'c (MPa).
        hef: effective embedment (mm).
        ca1: edge distance in the direction of shear (mm).
        da: nominal anchor diameter (mm).
        le: load-bearing length in shear (mm); defaults to min(hef, 8·da).
        cracked: True if concrete is cracked in service.
        n_anchors: anchors acting together (group simplified).

    Steel is always taken as Vsa = 0.60 · Ase_V · futa, which is **case (b)**
    of §17.7.1.2 — cast-in headed *bolt* and hooked-bolt anchors, and
    post-installed anchors whose sleeves do not cross the shear plane. It
    is the only case this function implements.

    **Sourcing.** The 0.60 coefficient is well corroborated. The (a)/(b)/(c)
    case split described here, the 1.0 coefficient attributed to headed
    studs, and the 0.80 grout-pad multiplier were reconstructed from
    secondary sources (code-reference sites and vendor design guides),
    **not** read from the printed standard. Verify against ACI 318-19
    before relying on the case boundaries; the number this function returns
    does not depend on them.

    **Not covered — case (a), welded headed studs.** ACI gives welded
    headed *studs* the higher Vsa = Ase_V · futa (coefficient 1.0, no 0.60).
    A welded stud is itself a cast-in headed anchor, so it falls squarely
    inside this module's declared scope, yet the signature carries no
    argument distinguishing a welded stud from a headed bolt: both are
    charged the conservative 0.60. Covering case (a) needs an explicit
    anchor-type input plus the AWS D1.1 welding precondition.

    **Not covered — anchors through a grout or mortar bed.** ACI reduces
    Vsa by a 0.80 multiplier for anchors in built-up grout pads — the usual
    condition for a column baseplate set on grout, so this is likely the
    most frequently applicable of the omissions listed here. There is no
    grout-pad argument, the multiplier is never applied, and this function
    is **unconservative** for that (common) case. Cited to ACI 318-14
    §17.5.1.3; the ACI 318-19 renumbering is **not verified** and the 0.80
    value comes from a secondary source. Kept as a declared limitation
    rather than an input: a ``grout_pad=True`` would ship a number whose
    -19 clause and value could not be verified.

    **futa cap not applied, and not previously stated here.** ACI caps futa
    at min(1.9·fya, 860 MPa). This function does not apply it: it receives
    no fya and uses futa as given. ``tension_capacity`` does not apply it
    either — it only states the cap as a condition on its futa argument,
    left to the caller. For futa > 1.9·fya the Vsa returned here is
    unconservative. Enforcing it would mean adding fya to a public
    signature.

    **Out of scope by module declaration — case (c), sleeves through the
    shear plane.** For post-installed anchors whose sleeve crosses the
    shear plane ACI requires Vsa from ACI 355.2 qualification testing; no
    closed form can stand in for it. This module declares itself to cover
    cast-in headed anchors only, so case (c) is outside its scope rather
    than a silent gap — but nothing in the signature enforces that, and a
    caller passing post-installed properties gets the case-(b) number back.

    **phi for steel in shear (corrected in 1.1.0).** Ductile steel in shear
    takes phi = 0.65 (ACI 318-19 Table 17.5.3; the ICC-ES evaluation
    reports issued under ACI 318-19 list 0.75 tension / 0.65 shear for
    ductile steel). This function used 0.75 for both, so a steel-governed
    phi_Vn was 0.75/0.65 = 1.15 times too high.
    """
    # Steel, §17.7.1.2 case (b): Vsa = 0.60·Ase_V·futa — cast-in headed bolt
    # or hooked bolt. NOT welded headed studs (case a, coefficient 1.0), and
    # no grout-pad 0.80 multiplier. See docstring.
    Vsa = 0.6 * n_anchors * Ase_V * futa

    # Breakout (17.7.2.1)
    if le is None:
        le = min(hef, 8.0 * da)
    Vb = 0.6 * (le / da) ** 0.2 * math.sqrt(da) * math.sqrt(fc) * ca1**1.5
    AVco = 4.5 * ca1 * ca1
    psi_ed_V = 1.0
    psi_c_V = 1.0 if cracked else 1.4
    Vcb = (AVco / AVco) * psi_ed_V * psi_c_V * Vb * n_anchors

    # Pryout (17.7.3.1): Vcp = kcp · Ncb
    kcp = 1.0 if hef < 65.0 else 2.0
    Nb = 10.0 * math.sqrt(fc) * hef**1.5
    Vcp = kcp * Nb * n_anchors

    Vn_steel = PHI_STEEL_SHEAR * Vsa
    cand = {"steel": Vn_steel,
            "breakout": PHI_CONCRETE * Vcb,
            "pryout":   PHI_CONCRETE * Vcp}
    phi_Vn = min(cand.values())
    governing = min(cand, key=cand.get)

    util = abs(Vu) / max(phi_Vn, 1e-9)
    return AnchorShearResult(
        Vsa=Vsa, Vcb=Vcb, Vcp=Vcp, phi_Vn=phi_Vn,
        governing=governing, Vu=Vu, utilization=util, ok=util <= 1.0,
    )


def interaction(
    *, Nu: float, phi_Nn: float, Vu: float, phi_Vn: float,
) -> AnchorInteractionResult:
    """Combined tension + shear per ACI 318-19 §17.8.3."""
    rn = abs(Nu) / max(phi_Nn, 1e-9)
    rv = abs(Vu) / max(phi_Vn, 1e-9)
    if rn <= 0.2:
        idx, rule = rv, "shear_only"
    elif rv <= 0.2:
        idx, rule = rn, "tension_only"
    else:
        idx, rule = rn ** (5.0 / 3.0) + rv ** (5.0 / 3.0), "combined_5/3"
    return AnchorInteractionResult(interaction=idx, rule=rule, ok=idx <= 1.0)


__all__ = [
    "AnchorCondition",
    "AnchorTensionResult", "AnchorShearResult", "AnchorInteractionResult",
    "tension_capacity", "shear_capacity", "interaction",
    "PHI_STEEL", "PHI_STEEL_SHEAR", "PHI_CONCRETE",
]
