"""Friccion negativa (downdrag) en pilote por consolidacion del terreno.

Calcula Q_neg = beta * sigma_v' * As por estratos sobre el plano neutro.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Layer:
    z_top_m: float
    z_bot_m: float
    gamma_kN_m3: float
    beta: float            # coeficiente NGI/Bjerrum (0.20-0.50 arcillas)
    consolidando: bool = True


@dataclass(frozen=True)
class FriccionNegativaInput:
    pile_diameter_m: float
    layers: tuple[Layer, ...]
    z_neutro_m: float       # plano neutro
    Q_dead_kN: float
    code: str = "EU"


@dataclass(frozen=True)
class FriccionNegativaResult:
    Q_neg_kN: float
    Q_total_servicio_kN: float
    code: str


def downdrag(inp: FriccionNegativaInput) -> FriccionNegativaResult:
    if inp.code not in {"EU", "AU", "SG", "US", "CO"}:
        raise ValueError(f"code invalido: {inp.code}")
    perim = 3.141592653589793 * inp.pile_diameter_m
    Q_neg = 0.0
    sigma_v = 0.0
    for L in inp.layers:
        z_top = L.z_top_m
        z_bot = min(L.z_bot_m, inp.z_neutro_m)
        if z_top >= inp.z_neutro_m:
            break
        if not L.consolidando:
            sigma_v += L.gamma_kN_m3 * (L.z_bot_m - L.z_top_m)
            continue
        dz = z_bot - z_top
        sigma_top = sigma_v
        sigma_bot = sigma_v + L.gamma_kN_m3 * dz
        sigma_mid = 0.5 * (sigma_top + sigma_bot)
        Q_neg += L.beta * sigma_mid * perim * dz
        sigma_v = sigma_bot
    return FriccionNegativaResult(Q_neg, inp.Q_dead_kN + Q_neg, inp.code)


__all__ = ["Layer", "FriccionNegativaInput", "FriccionNegativaResult", "downdrag"]
