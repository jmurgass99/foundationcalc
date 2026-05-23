"""AISC 360-22 design of steel beams and columns (LRFD).

Implements the most common checks for W-shapes (also valid for HSS/tubes
with the appropriate section properties supplied as inputs):

- **F2** Plastic moment, lateral-torsional buckling.
- **G2** Shear (uniform shear stress assumption).
- **E3 / E7** Compression with flexural buckling.
- **H1** Combined axial + bending interaction.

All formulas use LRFD phi-factors (phi_b = 0.90, phi_v = 0.90 or 1.00, phi_c = 0.90).
Inputs are dimensioned in **N, mm, MPa** by default; callers can pass any
consistent unit system as long as Fy and E share the same units.

References: ANSI/AISC 360-22, Specification for Structural Steel Buildings.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional


# Default LRFD resistance factors (AISC 360-22)
PHI_B = 0.90       # bending
PHI_V_DEFAULT = 0.90
PHI_C = 0.90       # compression


# ---------------------------------------------------------------------------
# Cross-section descriptor (minimal, decoupled from the SAP DB)
# ---------------------------------------------------------------------------

@dataclass
class SteelShape:
    """Minimal description of a doubly-symmetric I-shape.

    All length units must be consistent (e.g. mm). Areas in length squared,
    moduli in length cubed, inertias in length to the 4th power.
    """
    name: str
    A: float
    d: float        # overall depth
    bf: float       # flange width
    tf: float       # flange thickness
    tw: float       # web thickness
    Ix: float
    Iy: float
    Zx: float
    Sx: float
    Zy: float
    Sy: float
    rx: float
    ry: float
    J: float
    Cw: float       # warping constant
    h0: Optional[float] = None    # distance between flange centroids
    rts: Optional[float] = None   # AISC eq. F2-7

    def __post_init__(self):
        if self.h0 is None:
            self.h0 = self.d - self.tf
        if self.rts is None:
            # rts^2 = sqrt(Iy*Cw) / Sx  (F2-7)
            self.rts = math.sqrt(math.sqrt(self.Iy * self.Cw) / max(self.Sx, 1e-9))

    @classmethod
    def from_aisc(cls, name: str) -> "SteelShape":
        """Build a SteelShape from a catalog entry (EU or US I-shapes).

        Uses closed-form properties from fastsap.codes.aisc_360_db.
        For values that include fillet effects (AISC v15 Manual), override
        the relevant fields after the call.
        """
        from .aisc_360_db import aisc_w_properties
        p = aisc_w_properties(name)
        return cls(
            name=name,
            A=p["A"], d=p["d"], bf=p["bf"], tf=p["tf"], tw=p["tw"],
            Ix=p["Ix"], Iy=p["Iy"],
            Zx=p["Zx"], Sx=p["Sx"], Zy=p["Zy"], Sy=p["Sy"],
            rx=p["rx"], ry=p["ry"],
            J=p["J"], Cw=p["Cw"], h0=p["h0"],
        )


# ---------------------------------------------------------------------------
# F2 -- flexure of compact I-shapes
# ---------------------------------------------------------------------------

@dataclass
class BeamFlexureResult:
    Mp: float           # plastic moment
    Mn: float           # nominal moment (controls)
    phi_Mn: float       # design moment
    Lp: float           # plastic-limit unbraced length
    Lr: float           # inelastic-limit unbraced length
    Mr: float           # moment at Lr (yield + residual)
    regime: Literal["plastic", "inelastic_LTB", "elastic_LTB"]
    utilization: Optional[float] = None
    ok: Optional[bool] = None


def design_beam_flexure(shape: SteelShape, Lb: float, Fy: float,
                         Mu: float = 0.0, Cb: float = 1.0,
                         E: float = 200_000.0) -> BeamFlexureResult:
    """AISC F2 -- flexural strength of doubly-symmetric compact I-shapes.

    Args:
        shape: cross-section descriptor.
        Lb: unbraced length of the compression flange (mm).
        Fy: yield stress (MPa).
        Mu: required (factored) moment for utilisation; pass 0 to skip.
        Cb: lateral-torsional buckling modification factor.
        E: modulus of elasticity (default 200 GPa for steel).

    Returns:
        BeamFlexureResult.
    """
    Mp = Fy * shape.Zx                                          # eq. F2-1
    Lp = 1.76 * shape.ry * math.sqrt(E / Fy)                    # eq. F2-5
    rts = shape.rts
    h0 = shape.h0
    # Lr -- eq. F2-6
    inside = math.sqrt(
        (shape.J / max(shape.Sx * h0, 1e-12)) ** 2
        + 6.76 * (0.7 * Fy / E) ** 2
    )
    Lr = (1.95 * rts * (E / (0.7 * Fy))
          * math.sqrt(shape.J / max(shape.Sx * h0, 1e-12) + inside))
    # 0.7*Fy*Sx is the limit moment at L = Lr  (eq. F2-2 with FL=0.7Fy)
    Mr = 0.7 * Fy * shape.Sx

    if Lb <= Lp:
        Mn = Mp
        regime = "plastic"
    elif Lb <= Lr:
        # Linear interpolation, eq. F2-2
        Mn = min(Cb * (Mp - (Mp - Mr) * (Lb - Lp) / (Lr - Lp)), Mp)
        regime = "inelastic_LTB"
    else:
        # Elastic LTB, eq. F2-3 / F2-4
        Fcr = (Cb * math.pi ** 2 * E / (Lb / rts) ** 2
               * math.sqrt(1.0 + 0.078
                           * (shape.J / max(shape.Sx * h0, 1e-12))
                           * (Lb / rts) ** 2))
        Mn = min(Fcr * shape.Sx, Mp)
        regime = "elastic_LTB"

    phi_Mn = PHI_B * Mn
    res = BeamFlexureResult(
        Mp=Mp, Mn=Mn, phi_Mn=phi_Mn,
        Lp=Lp, Lr=Lr, Mr=Mr, regime=regime,
    )
    if Mu > 0:
        res.utilization = abs(Mu) / max(phi_Mn, 1e-12)
        res.ok = res.utilization <= 1.0
    return res


# ---------------------------------------------------------------------------
# G2 -- shear
# ---------------------------------------------------------------------------

@dataclass
class BeamShearResult:
    Vn: float
    phi_Vn: float
    Cv1: float
    utilization: Optional[float] = None
    ok: Optional[bool] = None


def design_beam_shear(shape: SteelShape, Fy: float, Vu: float = 0.0,
                       E: float = 200_000.0, kv: float = 5.34) -> BeamShearResult:
    """AISC G2 -- shear strength of rolled I-shapes.

    For rolled wide-flange shapes the G2.1(b)(i) exception gives
    phi_v = 1.00 and Cv1 = 1.0 when h/tw <= 2.24*sqrt(E/Fy). We apply that
    exception when applicable; otherwise we use eq. G2-3 / G2-4.
    """
    h = shape.d - 2 * shape.tf      # clear web depth (approx)
    Aw = shape.d * shape.tw
    h_tw = h / shape.tw

    if h_tw <= 2.24 * math.sqrt(E / Fy):
        phi_v = 1.00
        Cv1 = 1.0
    else:
        phi_v = PHI_V_DEFAULT
        lhs = 1.10 * math.sqrt(kv * E / Fy)
        if h_tw <= lhs:
            Cv1 = 1.0
        else:
            Cv1 = (1.10 * math.sqrt(kv * E / Fy)) / h_tw     # eq. G2-4

    Vn = 0.6 * Fy * Aw * Cv1                                  # eq. G2-1
    phi_Vn = phi_v * Vn
    res = BeamShearResult(Vn=Vn, phi_Vn=phi_Vn, Cv1=Cv1)
    if Vu > 0:
        res.utilization = abs(Vu) / max(phi_Vn, 1e-12)
        res.ok = res.utilization <= 1.0
    return res


# ---------------------------------------------------------------------------
# E3/E7 -- compression
# ---------------------------------------------------------------------------

@dataclass
class ColumnResult:
    Pn: float
    phi_Pn: float
    Fcr: float
    Fe: float
    KL_over_r: float
    regime: Literal["inelastic", "elastic"]
    utilization: Optional[float] = None
    ok: Optional[bool] = None


def design_column(shape: SteelShape, KL: float, Fy: float, Pu: float = 0.0,
                   E: float = 200_000.0,
                   axis: Literal["weak", "strong"] = "weak") -> ColumnResult:
    """AISC E3 -- compressive strength about the chosen axis.

    Uses r_y by default (weak axis governs for I-shapes with KLx = KLy).
    """
    r = shape.ry if axis == "weak" else shape.rx
    slenderness = KL / r
    Fe = math.pi ** 2 * E / max(slenderness ** 2, 1e-9)        # eq. E3-4
    boundary = 4.71 * math.sqrt(E / Fy)
    if slenderness <= boundary:
        Fcr = (0.658 ** (Fy / Fe)) * Fy                         # eq. E3-2
        regime = "inelastic"
    else:
        Fcr = 0.877 * Fe                                        # eq. E3-3
        regime = "elastic"
    Pn = Fcr * shape.A
    phi_Pn = PHI_C * Pn
    res = ColumnResult(
        Pn=Pn, phi_Pn=phi_Pn, Fcr=Fcr, Fe=Fe,
        KL_over_r=slenderness, regime=regime,
    )
    if Pu > 0:
        res.utilization = abs(Pu) / max(phi_Pn, 1e-12)
        res.ok = res.utilization <= 1.0
    return res


# ---------------------------------------------------------------------------
# H1 -- combined axial + bending
# ---------------------------------------------------------------------------

@dataclass
class InteractionResult:
    interaction: float
    formula: Literal["H1-1a", "H1-1b"]
    ok: bool


def interaction_H1(Pu: float, phi_Pn: float,
                    Mux: float, phi_Mnx: float,
                    Muy: float = 0.0, phi_Mny: float = 1.0) -> InteractionResult:
    """AISC H1 -- combined axial compression + biaxial bending (LRFD).

    Selects eq. H1-1a when Pu/phi_Pn >= 0.2, otherwise H1-1b.

    Args:
        Pu: required axial (N), positive = compression.
        phi_Pn: design compressive strength (N).
        Mux: required moment about x-axis (N*mm).
        phi_Mnx: design flexural strength about x-axis (N*mm).
        Muy: required moment about y-axis (N*mm); default 0.
        phi_Mny: design flexural strength about y-axis (N*mm); default 1.

    Returns:
        InteractionResult with interaction ratio and governing formula.
    """
    ratio_axial = abs(Pu) / max(phi_Pn, 1e-12)
    ratio_mx = abs(Mux) / max(phi_Mnx, 1e-12)
    ratio_my = abs(Muy) / max(phi_Mny, 1e-12)

    if ratio_axial >= 0.2:
        # eq. H1-1a
        interaction = ratio_axial + (8.0 / 9.0) * (ratio_mx + ratio_my)
        formula: Literal["H1-1a", "H1-1b"] = "H1-1a"
    else:
        # eq. H1-1b
        interaction = ratio_axial / 2.0 + (ratio_mx + ratio_my)
        formula = "H1-1b"

    return InteractionResult(
        interaction=interaction,
        formula=formula,
        ok=interaction <= 1.0,
    )
