"""Rigideces de interacción suelo-estructura (Winkler / Gazetas) para
zapatas superficiales rectangulares sobre suelo estratificado.

Calcula resortes equivalentes Kx, Ky, Kz, Krx, Kry, Krz que pueden ser
exportados al modelo SAP/ETABS via fastsap.oapi_overrides.

Referencias:
    - Gazetas (1991) "Foundation Vibrations" Handbook of Geotechnical Eng.
    - Bowles (1996) "Foundation Analysis and Design", 5a ed., cap. 9.
    - NIST GCR 12-917-21 "Soil-Structure Interaction for Building Structures"

NOTA: Este modulo define un `SoilLayer` propio (dataclass con Vs, rho, nu)
distinto del `core.soil.SoilLayer` (Pydantic, parametros EC7). Ambos coexisten
porque describen aspectos diferentes del suelo (dinamico vs. estatico/EC7).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Union


@dataclass(frozen=True)
class SoilLayer:
    """Estrato horizontal con propiedades elasticas equivalentes (dinamicas)."""

    thickness: float       # m
    Vs: float              # velocidad de onda S m/s
    rho: float = 1900.0    # densidad kg/m^3
    nu: float = 0.3        # coef. Poisson

    @property
    def G(self) -> float:
        """Modulo de corte G = rho * Vs^2  [Pa]."""
        return self.rho * self.Vs ** 2

    @property
    def E(self) -> float:
        """Modulo de Young E = 2*G*(1+nu)  [Pa]."""
        return 2.0 * self.G * (1.0 + self.nu)


@dataclass(frozen=True)
class FootingGeometry:
    """Zapata rectangular superficial alineada con ejes X, Y.

    Atributos:
        L: longitud m (eje X, mayor lado generalmente)
        B: ancho m (eje Y, menor lado)
        embedment: profundidad de empotramiento m (0 = en superficie)
    """

    L: float
    B: float
    embedment: float = 0.0


@dataclass
class WinklerStiffness:
    """Rigideces de resorte equivalentes (N/m traslacion, N*m/rad rotacion)."""

    Kx: float   # traslacion X
    Ky: float   # traslacion Y
    Kz: float   # traslacion Z (vertical)
    Krx: float  # rotacion alrededor X (rocking en plano Y-Z)
    Kry: float  # rotacion alrededor Y (rocking en plano X-Z)
    Krz: float  # torsion alrededor Z

    def as_tuple(self) -> tuple:
        """Tupla en orden CSI: (Kx, Ky, Kz, Krx, Kry, Krz)."""
        return (self.Kx, self.Ky, self.Kz, self.Krx, self.Kry, self.Krz)


def _equivalent_layer(layers: List[SoilLayer], depth_influence: float) -> SoilLayer:
    """Promedio ponderado por espesor de las primeras capas hasta `depth_influence`.

    Si la suma de espesores no alcanza la profundidad de influencia, se usa la
    ultima capa para el remanente.
    """
    total = 0.0
    G_acc = 0.0
    rho_acc = 0.0
    nu_acc = 0.0
    for layer in layers:
        remaining = depth_influence - total
        if remaining <= 0:
            break
        take = min(layer.thickness, remaining)
        G_acc += layer.G * take
        rho_acc += layer.rho * take
        nu_acc += layer.nu * take
        total += take
    if total < depth_influence and layers:
        last = layers[-1]
        gap = depth_influence - total
        G_acc += last.G * gap
        rho_acc += last.rho * gap
        nu_acc += last.nu * gap
        total += gap
    if total <= 0:
        raise ValueError("Perfil de suelo vacio o profundidad de influencia 0")
    G_avg = G_acc / total
    rho_avg = rho_acc / total
    nu_avg = nu_acc / total
    Vs_avg = math.sqrt(G_avg / rho_avg)
    return SoilLayer(thickness=total, Vs=Vs_avg, rho=rho_avg, nu=nu_avg)


def gazetas_stiffness(
    footing: FootingGeometry,
    soil: Union[List[SoilLayer], SoilLayer],
) -> WinklerStiffness:
    """Calcula rigideces de Gazetas para zapata rectangular rigida.

    Formulas de Gazetas (1991) tal como las recoge NIST GCR 12-917-21
    (Tabla 2-2a), con L y B las SEMIDIMENSIONES (la zapata mide 2L × 2B,
    L >= B) e I_bx, I_by, J_t de la superficie de contacto completa:
        Kz   = 2*G*L / (1-nu) * [0.73 + 1.54*(B/L)^0.75]
        Ky   = 2*G*L / (2-nu) * [2.0 + 2.5*(B/L)^0.85]
        Kx   = Ky - 0.2*G*L / (0.75-nu) * [1 - (B/L)]
        Krx  = G/(1-nu) * I_bx^0.75 * (L/B)^0.25 * (2.4 + 0.5*B/L)
        Kry  = G/(1-nu) * I_by^0.75 * 3 * (L/B)^0.15
        Krz  = G * J_t^0.75 * [4 + 11*(1 - B/L)^10]

    `FootingGeometry` recibe las dimensiones COMPLETAS; aqui se dividen por 2.

    DEFECTO CORREGIDO (1.1.0): las traslaciones usaban la longitud completa
    donde la formula pide la semilongitud (Kz, Ky y Kx el doble: zapata de
    2 × 2 m, G = 76 MPa, nu = 0,35 -> Kz 1 061 662 en vez de 530 831 kN/m),
    Kry llevaba (3 + 0,5·B/L) en lugar de 3 (+17 % en cuadrada) y Krz era
    3,5·G·J^0,75 sin el termino de forma (-12,5 % en cuadrada).

    Para suelo estratificado, usa _equivalent_layer hasta depth ~= 2*B.
    """
    if isinstance(soil, SoilLayer):
        layer = soil
    else:
        depth_inf = 2.0 * min(footing.L, footing.B)
        layer = _equivalent_layer(soil, depth_inf)
    G = layer.G
    nu = layer.nu
    L = max(footing.L, footing.B)       # dimension completa mayor
    B = min(footing.L, footing.B)       # dimension completa menor
    ratio = B / L
    L_half = L / 2.0                    # Gazetas trabaja con 2L x 2B
    # Traslaciones (Gazetas 1991, semilongitud)
    Kz = 2.0 * G * L_half / (1.0 - nu) * (0.73 + 1.54 * ratio ** 0.75)
    Ky = 2.0 * G * L_half / (2.0 - nu) * (2.0 + 2.5 * ratio ** 0.85)
    Kx = Ky - 0.2 * G * L_half / (0.75 - nu) * (1.0 - ratio)
    # Rotaciones (rocking): inercias de la superficie de contacto completa
    I_bx = (L * B ** 3) / 12.0      # inercia alrededor X
    I_by = (B * L ** 3) / 12.0      # inercia alrededor Y
    Krx = G / (1.0 - nu) * I_bx ** 0.75 * (L / B) ** 0.25 * (2.4 + 0.5 * ratio)
    Kry = G / (1.0 - nu) * I_by ** 0.75 * 3.0 * (L / B) ** 0.15
    # Torsion: J_t = I_bx + I_by (momento polar de la superficie de contacto)
    J_t = I_bx + I_by
    Krz = G * J_t ** 0.75 * (4.0 + 11.0 * (1.0 - ratio) ** 10)
    return WinklerStiffness(Kx=Kx, Ky=Ky, Kz=Kz, Krx=Krx, Kry=Kry, Krz=Krz)


__all__ = [
    "SoilLayer",
    "FootingGeometry",
    "WinklerStiffness",
    "gazetas_stiffness",
]
