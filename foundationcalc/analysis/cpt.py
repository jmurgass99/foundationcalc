"""Cone Penetration Test (CPT) processing and parameter correlations.

CPT data has three measured channels at each depth:
- q_c   cone resistance (MPa)
- f_s   sleeve friction (kPa)
- u_2   pore-water pressure measured behind the cone (kPa)

Derived quantities used by the SBT (Soil Behaviour Type) and parameter
correlations:
- q_t = q_c + (1 - a) · u_2     net cone resistance corrected for area ratio
- R_f = f_s / q_t · 100          friction ratio (%)
- σ_v0   total vertical stress (kPa)
- σ'_v0  effective vertical stress (kPa)
- Q_t = (q_t − σ_v0) / σ'_v0     normalised cone resistance
- F_r = f_s / (q_t − σ_v0) · 100  normalised friction ratio (%)

Sources implemented (re-derived from primary references, MIT-style
re-implementation — no GPL contamination):
- **Robertson (2010)** non-normalised SBT chart with the soil behaviour
  type index `I_SBT`.
- **Robertson & Wride (1998)** + **Robertson (2009)** normalised SBT
  with index `I_c`.
- **Kulhawy & Mayne (1990)** for φ' from Q_t (sand).
- **Mayne (2007)** undrained shear strength c_u from q_t and N_kt.
- **Robertson (2009)** Young's modulus E from Q_t.

Theory: docs/theory/10_in_situ_tests.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, Tuple

import numpy as np
from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Robertson 2010 SBT classification
# ---------------------------------------------------------------------------

class SBTZone(int, Enum):
    """Robertson 2010 SBT zones (non-normalised, I_SBT)."""

    SENSITIVE_FINE = 1            # I_SBT < 1.31
    ORGANIC_CLAY = 2              # depends on q_c & R_f
    CLAY = 3                      # 2.05 ≤ I_SBT < 2.60 with q_c moderate
    SILT_MIX_CLAY = 4             # 2.60 ≤ I_SBT < 2.95
    SAND_MIX = 5                  # 2.95 ≤ I_SBT < 3.60
    SAND = 6                      # 3.60 ≤ I_SBT
    DENSE_SAND_GRAVEL = 7         # very high q_c
    STIFF_SAND_CLAY = 8           # overconsolidated stiff
    STIFF_FINE_GRAINED = 9        # OC clay


def _safe_log10(x: float) -> float:
    return math.log10(max(x, 1e-6))


def i_sbt_robertson_2010(q_t_MPa: float, R_f_pct: float, p_a_MPa: float = 0.1) -> float:
    """Non-normalised Robertson (2010) soil behaviour type index.

    I_SBT = ((3.47 − log10(q_t/p_a))² + (log10(R_f) + 1.22)²)^0.5

    Args:
        q_t_MPa: cone tip resistance corrected for pore pressure (MPa).
        R_f_pct: friction ratio (%).
        p_a_MPa: atmospheric pressure (MPa, default 0.1).
    """
    a = 3.47 - _safe_log10(q_t_MPa / p_a_MPa)
    b = _safe_log10(R_f_pct) + 1.22
    return math.sqrt(a * a + b * b)


def i_c_robertson_2009(Q_t: float, F_r_pct: float) -> float:
    """Normalised Robertson (2009) soil-behaviour-type index.

    I_c = ((3.47 − log10(Q_t))² + (log10(F_r) + 1.22)²)^0.5
    """
    a = 3.47 - _safe_log10(Q_t)
    b = _safe_log10(F_r_pct) + 1.22
    return math.sqrt(a * a + b * b)


def sbt_zone_from_i_sbt(i_sbt: float) -> SBTZone:
    """Map I_SBT (Robertson 2010) → SBT zone (simplified)."""
    if i_sbt < 1.31:
        return SBTZone.DENSE_SAND_GRAVEL
    if i_sbt < 2.05:
        return SBTZone.SAND
    if i_sbt < 2.60:
        return SBTZone.SAND_MIX
    if i_sbt < 2.95:
        return SBTZone.SILT_MIX_CLAY
    if i_sbt < 3.60:
        return SBTZone.CLAY
    return SBTZone.ORGANIC_CLAY


def sbt_zone_from_i_c(i_c: float) -> SBTZone:
    """Map I_c (Robertson 2009 normalised) → SBT zone.

    | I_c range | Zone | Description |
    |---|---|---|
    | < 1.31 | 7 | Gravelly sand to dense sand |
    | 1.31 – 2.05 | 6 | Sand: clean sand to silty sand |
    | 2.05 – 2.60 | 5 | Sand mixtures: silty sand to sandy silt |
    | 2.60 – 2.95 | 4 | Silt mixtures: clayey silt to silty clay |
    | 2.95 – 3.60 | 3 | Clays: clay to silty clay |
    | > 3.60 | 2 | Organic soils — clay |
    """
    return sbt_zone_from_i_sbt(i_c)  # same boundaries


# ---------------------------------------------------------------------------
# Parameter correlations
# ---------------------------------------------------------------------------

def phi_from_qt_kulhawy_mayne(
    q_t_MPa: float, sigma_v0_eff_MPa: float, p_a_MPa: float = 0.1
) -> float:
    """Effective friction angle φ' from normalised cone resistance.

    Kulhawy & Mayne (1990):  φ' = 17.6 + 11 · log10[(q_t / p_a) / √(σ'_v0 / p_a)]   (deg)

    Valid for clean sands; do not use for clays.
    """
    if sigma_v0_eff_MPa <= 0:
        raise ValueError("Effective overburden must be > 0.")
    Q_tn = (q_t_MPa / p_a_MPa) / math.sqrt(sigma_v0_eff_MPa / p_a_MPa)
    return 17.6 + 11.0 * _safe_log10(Q_tn)


def cu_from_qt(
    q_t_kPa: float, sigma_v0_kPa: float, N_kt: float = 14.0
) -> float:
    """Undrained shear strength from cone resistance.

    c_u = (q_t − σ_v0) / N_kt

    N_kt typically 10–20 (Mayne 2007 recommends 14 as a default for soft to
    medium clays; site-specific calibration is preferred).
    """
    if N_kt <= 0:
        raise ValueError("N_kt must be > 0.")
    return max((q_t_kPa - sigma_v0_kPa) / N_kt, 0.0)


def E_from_qt_robertson(q_t_MPa: float, sigma_v0_eff_MPa: float, p_a_MPa: float = 0.1,
                        alpha: Optional[float] = None) -> float:
    """Young's modulus from cone resistance (Robertson, 2009).

    E = α · (q_t − σ_v0)

    If α is None, use a default from Robertson 2009 nomograph:
        α ≈ 0.015 · (10 ** (0.55 · I_c + 1.68))
    For clean sands α typically 3–8; for clays 1–3.

    Returns E in the same units as (q_t − σ_v0).
    """
    if alpha is None:
        alpha = 5.0  # clean sand default
    return max(alpha * (q_t_MPa - sigma_v0_eff_MPa), 0.0)


def relative_density_kulhawy_mayne(
    q_t_MPa: float, sigma_v0_eff_MPa: float, p_a_MPa: float = 0.1, OCR: float = 1.0,
) -> float:
    """Relative density D_R (%) from normalised cone resistance.

    Kulhawy & Mayne (1990):
        D_R² = Q_tn / (305 · Q_OCR)
    with Q_OCR = OCR^0.18 (default 1.0 for normally consolidated).
    """
    if sigma_v0_eff_MPa <= 0:
        raise ValueError("Effective overburden must be > 0.")
    Q_tn = (q_t_MPa / p_a_MPa) / math.sqrt(sigma_v0_eff_MPa / p_a_MPa)
    Q_OCR = OCR ** 0.18
    Dr_sq = Q_tn / (305.0 * Q_OCR)
    Dr = math.sqrt(max(Dr_sq, 0.0))
    return min(max(Dr * 100.0, 0.0), 100.0)


# ---------------------------------------------------------------------------
# CPT profile container
# ---------------------------------------------------------------------------

class CPTReading(BaseModel):
    """One depth-resolved CPT data row."""

    depth: float = Field(..., ge=0, description="Depth from surface (m)")
    q_c_MPa: float = Field(..., ge=0, description="Cone resistance (MPa)")
    f_s_kPa: float = Field(0.0, ge=0, description="Sleeve friction (kPa)")
    u_2_kPa: float = Field(0.0, description="Pore-water pressure behind cone (kPa)")
    a_n: float = Field(0.8, gt=0, le=1.0, description="Net area ratio (typically 0.75–0.85)")

    @property
    def q_t_MPa(self) -> float:
        """Corrected cone resistance q_t = q_c + (1 − a_n) · u_2 / 1000."""
        return self.q_c_MPa + (1.0 - self.a_n) * self.u_2_kPa / 1000.0

    def R_f_pct(self) -> float:
        denom = self.q_t_MPa * 1000.0  # → kPa
        if denom <= 0:
            return 0.0
        return self.f_s_kPa / denom * 100.0


@dataclass
class CPTLayerSummary:
    """Aggregated layer derived from a CPT profile interval."""

    z_top: float
    z_bot: float
    q_t_avg_MPa: float
    f_s_avg_kPa: float
    R_f_avg_pct: float
    I_c_avg: float
    sbt_zone: SBTZone
    phi_deg: Optional[float] = None
    c_u_kPa: Optional[float] = None
    E_MPa: Optional[float] = None
    relative_density_pct: Optional[float] = None


class CPTProfile(BaseModel):
    """A complete CPT log + helpers to compute stresses and parameters."""

    readings: List[CPTReading]
    water_table_depth_m: float = Field(0.0, ge=0, description="Water table from surface (m)")
    gamma_above_wt_kN_m3: float = Field(18.0, gt=10)
    gamma_below_wt_kN_m3: float = Field(20.0, gt=10)
    gamma_w_kN_m3: float = Field(9.81, gt=0)

    @model_validator(mode="after")
    def _check_sorted(self):
        if any(self.readings[i + 1].depth <= self.readings[i].depth
               for i in range(len(self.readings) - 1)):
            raise ValueError("Readings must be in strictly increasing depth order.")
        return self

    def total_stress_kPa(self, depth: float) -> float:
        """Total vertical stress σ_v0 at `depth`: γ_above above the water table, γ_below under it.

        DEFECTO CORREGIDO (1.1.0): se acumulaba tramo a tramo entre lecturas y
        el último tramo (de la lectura anterior a `depth`) usaba SIEMPRE γ sobre
        el freático (las dos ramas del condicional eran iguales), y los tramos
        que cruzaban el freático no se partían. Con lecturas cada 0,2 m daba
        73,8 kPa en vez de 74,0 a 4 m. Como los pesos específicos son del
        perfil, no de cada lectura, la tensión es la expresión cerrada.
        """
        if depth <= 0:
            return 0.0
        wt = self.water_table_depth_m
        above = min(depth, wt)
        below = max(depth - wt, 0.0)
        return self.gamma_above_wt_kN_m3 * above + self.gamma_below_wt_kN_m3 * below

    def effective_stress_kPa(self, depth: float) -> float:
        sigma = self.total_stress_kPa(depth)
        u = max(depth - self.water_table_depth_m, 0.0) * self.gamma_w_kN_m3
        return sigma - u

    def Q_t(self, reading: CPTReading) -> float:
        sigma_v0 = self.total_stress_kPa(reading.depth)
        sigma_v0_eff = self.effective_stress_kPa(reading.depth)
        if sigma_v0_eff <= 0:
            return 0.0
        return (reading.q_t_MPa * 1000.0 - sigma_v0) / sigma_v0_eff

    def F_r_pct(self, reading: CPTReading) -> float:
        sigma_v0 = self.total_stress_kPa(reading.depth)
        denom = reading.q_t_MPa * 1000.0 - sigma_v0
        if denom <= 0:
            return 0.0
        return reading.f_s_kPa / denom * 100.0

    def i_c(self, reading: CPTReading) -> float:
        Q_t = self.Q_t(reading)
        F_r = self.F_r_pct(reading)
        if Q_t <= 0 or F_r <= 0:
            return 0.0
        return i_c_robertson_2009(Q_t, F_r)

    def sbt_zone(self, reading: CPTReading) -> SBTZone:
        return sbt_zone_from_i_c(self.i_c(reading))

    # ----------------------------------------------------------- layering
    def stratify(self, n_layers: int = 4) -> List[CPTLayerSummary]:
        """Aggregate the CPT profile into `n_layers` equal-depth bands.

        Each layer summary contains the average q_t, f_s, R_f, I_c, derived
        SBT zone and the EC7-relevant parameters (φ, c_u, E, D_R).
        """
        if not self.readings:
            return []
        z_min = self.readings[0].depth
        z_max = self.readings[-1].depth
        edges = [z_min + (z_max - z_min) * i / n_layers for i in range(n_layers + 1)]
        summaries: List[CPTLayerSummary] = []
        for k in range(n_layers):
            z_top, z_bot = edges[k], edges[k + 1]
            inside = [r for r in self.readings if z_top <= r.depth <= z_bot]
            if not inside:
                continue
            q_t = np.mean([r.q_t_MPa for r in inside])
            f_s = np.mean([r.f_s_kPa for r in inside])
            R_f = np.mean([r.R_f_pct() for r in inside])
            I_c = np.mean([self.i_c(r) for r in inside])
            zone = sbt_zone_from_i_c(float(I_c))
            phi = c_u = E = Dr = None
            sigma_v0 = self.total_stress_kPa(0.5 * (z_top + z_bot))
            sigma_v0_eff = self.effective_stress_kPa(0.5 * (z_top + z_bot))
            if zone in (SBTZone.SAND, SBTZone.SAND_MIX, SBTZone.DENSE_SAND_GRAVEL):
                phi = phi_from_qt_kulhawy_mayne(float(q_t), sigma_v0_eff / 1000.0)
                E = E_from_qt_robertson(float(q_t), sigma_v0_eff / 1000.0)
                Dr = relative_density_kulhawy_mayne(float(q_t), sigma_v0_eff / 1000.0)
            elif zone in (SBTZone.CLAY, SBTZone.SILT_MIX_CLAY, SBTZone.ORGANIC_CLAY):
                c_u = cu_from_qt(float(q_t) * 1000.0, sigma_v0)
                E = E_from_qt_robertson(float(q_t), sigma_v0_eff / 1000.0, alpha=2.0)
            summaries.append(CPTLayerSummary(
                z_top=z_top, z_bot=z_bot,
                q_t_avg_MPa=float(q_t),
                f_s_avg_kPa=float(f_s),
                R_f_avg_pct=float(R_f),
                I_c_avg=float(I_c),
                sbt_zone=zone,
                phi_deg=phi, c_u_kPa=c_u, E_MPa=E,
                relative_density_pct=Dr,
            ))
        return summaries


__all__ = [
    "SBTZone",
    "CPTReading",
    "CPTLayerSummary",
    "CPTProfile",
    "i_sbt_robertson_2010",
    "i_c_robertson_2009",
    "sbt_zone_from_i_sbt",
    "sbt_zone_from_i_c",
    "phi_from_qt_kulhawy_mayne",
    "cu_from_qt",
    "E_from_qt_robertson",
    "relative_density_kulhawy_mayne",
]
