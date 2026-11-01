"""Separación Semántica -> Malla Subdividida (SoilSublayerMapping) para FoundationCalc.

Mapea estratos geotécnicos semánticos (`layer_to_sublayers`) y pilotes (`pile_to_segments`)
a una malla discreta de subcapas de consolidación 1D y bulbo de tensiones 2:1 / Boussinesq,
preservando índices de compresión, drenaje y presiones efectivas al cambiar `divisions`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .analysis.consolidation import ClayLayer, U_from_Tv, settlement_consolidation


@dataclass(frozen=True)
class SemanticSoilLayer:
    id: str
    thickness_m: float
    gamma_eff_kN_m3: float
    e0: float
    C_c: float
    C_r: float = 0.04
    OCR: float = 1.0
    c_v_m2_per_year: float = 2.5


@dataclass
class SoilSublayerMapping:
    """Mapeo explícito Estrato Semántico -> Subcapas Discretas."""
    layer_to_sublayers: Dict[str, List[int]] = field(default_factory=dict)
    sublayer_to_layer: Dict[int, str] = field(default_factory=dict)
    pile_to_segments: Dict[str, List[int]] = field(default_factory=dict)


@dataclass
class SublayerNode:
    index: int
    layer_id: str
    z_mid_m: float
    dz_m: float
    sigma_v0_kPa: float
    delta_sigma_kPa: float
    settlement_mm: float


def build_foundation_sublayer_mesh(
    B_m: float,
    L_m: float,
    q_net_kPa: float,
    layers: List[SemanticSoilLayer],
    divisions_per_layer: int = 5,
    time_years: float = 2.0,
) -> Tuple[List[SublayerNode], SoilSublayerMapping, Dict[str, float]]:
    """Subdivide cada estrato en `divisions_per_layer` subcapas y calcula asiento y consolidación."""
    div = max(1, int(divisions_per_layer))
    mapping = SoilSublayerMapping()
    sublayers: List[SublayerNode] = []

    total_H = sum(layer.thickness_m for layer in layers)
    c_v_avg = sum(l.c_v_m2_per_year * l.thickness_m for l in layers) / max(total_H, 1e-6)
    H_dr = total_H / 2.0
    T_v = c_v_avg * time_years / max(H_dr ** 2, 1e-9)
    U_deg = U_from_Tv(T_v)

    z_cursor = 0.0
    sigma_cursor = 10.0  # sobrecarga efectiva inicial en cota de desplante (kPa)

    for layer in layers:
        dz = layer.thickness_m / div
        mapping.layer_to_sublayers[layer.id] = []
        for _ in range(div):
            idx = len(sublayers)
            z_mid = z_cursor + 0.5 * dz
            sigma_v0 = sigma_cursor + 0.5 * dz * layer.gamma_eff_kN_m3
            # Bulbo 2:1 bajo zapata rectangular B x L
            delta_sigma = q_net_kPa * (B_m * L_m) / ((B_m + z_mid) * (L_m + z_mid))
            clay_sub = ClayLayer(
                thickness_m=dz,
                e0=layer.e0,
                C_c=layer.C_c,
                C_r=layer.C_r,
                OCR=layer.OCR,
                sigma_p_kPa=max(sigma_v0 * layer.OCR, sigma_v0 + 1.0),
                c_v_m2_per_year=layer.c_v_m2_per_year,
                two_way_drainage=True,
            )
            s_ult_m = settlement_consolidation(clay_sub, sigma_v0, delta_sigma)
            sublayers.append(
                SublayerNode(
                    index=idx,
                    layer_id=layer.id,
                    z_mid_m=z_mid,
                    dz_m=dz,
                    sigma_v0_kPa=sigma_v0,
                    delta_sigma_kPa=delta_sigma,
                    settlement_mm=s_ult_m * 1000.0,
                )
            )
            mapping.layer_to_sublayers[layer.id].append(idx)
            mapping.sublayer_to_layer[idx] = layer.id
            z_cursor += dz
            sigma_cursor += dz * layer.gamma_eff_kN_m3

    # Mapeo de fuste de pilote equivalente en los mismos segmentos de profundidad
    mapping.pile_to_segments["PILE-1"] = list(range(len(sublayers)))

    s_total_ult_mm = sum(s.settlement_mm for s in sublayers)
    summary = {
        "total_thickness_m": total_H,
        "T_v": T_v,
        "U_degree": U_deg,
        "s_ult_mm": s_total_ult_mm,
        "s_t_mm": s_total_ult_mm * U_deg,
        "sublayer_count": float(len(sublayers)),
    }
    return sublayers, mapping, summary
