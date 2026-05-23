"""
Bridge FoundationDesignJm → GeoJm.

Consume las curvas P-y de GeoJm y el modelo Mander para nutrir el
diseño de pile_cap y pile_lateral en FoundationDesignJm sin duplicar
implementaciones.

Si GeoJm no está instalado, las funciones devuelven ``None`` y emiten
warning — el resto del pipeline sigue funcionando.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Any


def get_py_matlock(z_m: float, D_m: float, su_kPa: float, **kwargs) -> Any:
    """Devuelve curva P-y Matlock vía GeoJm (o None si no disponible)."""
    try:
        from geojm.piles import py_matlock_soft_clay
    except ImportError:
        warnings.warn("GeoJm no instalado — fallback heurístico", RuntimeWarning)
        return None
    return py_matlock_soft_clay(z_m=z_m, D_m=D_m, su_kPa=su_kPa, **kwargs)


def get_py_reese(z_m: float, D_m: float, phi_deg: float, **kwargs) -> Any:
    """Devuelve curva P-y Reese (arena) vía GeoJm."""
    try:
        from geojm.piles import py_reese_sand
    except ImportError:
        warnings.warn("GeoJm no instalado — fallback heurístico", RuntimeWarning)
        return None
    return py_reese_sand(z_m=z_m, D_m=D_m, phi_deg=phi_deg, **kwargs)


def get_mander_material(fc: float, fyh: float, rho_x: float, rho_y: float,
                         **kwargs) -> Any:
    """Devuelve material hormigón confinado Mander vía GeoJm."""
    try:
        from geojm.materials import mander_confined_concrete
    except ImportError:
        warnings.warn("GeoJm no instalado", RuntimeWarning)
        return None
    return mander_confined_concrete(fc=fc, fyh=fyh, rho_x=rho_x,
                                     rho_y=rho_y, **kwargs)


def get_pile_group_efficiency(s_over_D: float, rows: int) -> Any:
    """Eficiencia de grupo vía GeoJm."""
    try:
        from geojm.piles import pile_group_efficiency_lateral
    except ImportError:
        warnings.warn("GeoJm no instalado", RuntimeWarning)
        return None
    return pile_group_efficiency_lateral(s_over_D=s_over_D, rows=rows)



# ---------------------------------------------------------------------------
# FD-001: Higher-level bridges consumed by pile_cap / pile_lateral design
# ---------------------------------------------------------------------------

@dataclass
class PYSpring:
    """Discrete p-y spring at a given depth."""
    depth_m: float
    k_kN_m2: float          # secant stiffness (kN/m per m of pile)
    p_ult_kN_m: float       # ultimate resistance (kN/m)
    soil_type: str           # "clay" or "sand"


@dataclass
class ManderConfinedConcrete:
    """Mander confined concrete output tuple."""
    fcc: float       # confined compressive strength (MPa)
    eps_cc: float    # strain at peak confined stress
    eps_cu: float    # ultimate confined strain

    def __iter__(self):
        """Allow tuple-unpacking: fcc, eps_cc, eps_cu = result."""
        return iter((self.fcc, self.eps_cc, self.eps_cu))


@dataclass
class PileLayerData:
    """Input layer description for get_py_springs_from_geojm.

    Each layer is either clay (su_kPa provided) or sand (phi_deg provided).
    """
    z_top_m: float
    z_bot_m: float
    soil_type: str = "clay"       # "clay" or "sand"
    su_kPa: float = 0.0          # undrained shear strength (clay)
    phi_deg: float = 0.0         # friction angle (sand)
    gamma_eff: float = 9.0       # effective unit weight (kN/m3)


def get_py_springs_from_geojm(
    pile_data: list[PileLayerData],
    D_m: float = 0.6,
    n_springs: int = 20,
) -> list[PYSpring]:
    """Build a list of p-y springs along a pile from soil layer data.

    Uses GeoJm Matlock (clay) / Reese (sand) if available; otherwise
    falls back to the local ``pile_lateral`` module formulations so that
    the pipeline never breaks.

    Args:
        pile_data: ordered list of soil layers from surface downward.
        D_m: pile diameter (m).
        n_springs: total number of springs to distribute along the pile.

    Returns:
        List of ``PYSpring`` objects from the top to the tip.
    """
    if not pile_data:
        return []

    z_min = min(ld.z_top_m for ld in pile_data)
    z_max = max(ld.z_bot_m for ld in pile_data)
    dz = (z_max - z_min) / max(n_springs, 1)
    y_ref = 0.01 * D_m  # 1 % of diameter as reference deflection

    springs: list[PYSpring] = []
    for i in range(n_springs):
        z = z_min + (i + 0.5) * dz
        # Find the layer at depth z
        layer = None
        for ld in pile_data:
            if ld.z_top_m <= z <= ld.z_bot_m:
                layer = ld
                break
        if layer is None:
            layer = pile_data[-1]

        if layer.soil_type == "clay":
            p_val = _py_spring_clay(z, D_m, layer.su_kPa,
                                    layer.gamma_eff, y_ref)
        else:
            p_val = _py_spring_sand(z, D_m, layer.phi_deg,
                                    layer.gamma_eff, y_ref)

        k_secant = abs(p_val / y_ref) if abs(y_ref) > 1e-12 else 0.0
        # Ultimate resistance estimate
        if layer.soil_type == "clay":
            p_u = min(9.0 * layer.su_kPa * D_m,
                      (3.0 + layer.gamma_eff * z / max(layer.su_kPa, 1)
                       + 0.5 * z / D_m) * layer.su_kPa * D_m)
        else:
            phi_r = math.radians(layer.phi_deg)
            K_p = math.tan(math.pi / 4 + phi_r / 2) ** 2
            p_u = layer.gamma_eff * z * D_m * (K_p ** 2 - 1) if z > 0 else 0.0

        springs.append(PYSpring(
            depth_m=z, k_kN_m2=k_secant,
            p_ult_kN_m=max(p_u, 0.0), soil_type=layer.soil_type,
        ))
    return springs


def _py_spring_clay(z_m: float, D_m: float, su_kPa: float,
                    gamma_eff: float, y_ref: float) -> float:
    """Compute p at y_ref for clay -- GeoJm or local fallback."""
    result = get_py_matlock(z_m=z_m, D_m=D_m, su_kPa=su_kPa)
    if result is not None:
        # GeoJm returns (p_array, y_array); interpolate at y_ref
        import numpy as np
        p_arr, y_arr = result
        return float(np.interp(y_ref, y_arr, p_arr))
    # Fallback: local Matlock
    from ..analysis.pile_lateral import py_matlock
    return py_matlock(y_m=y_ref, depth_m=z_m, pile_D_m=D_m,
                      c_u_kPa=su_kPa, gamma_eff_kN_m3=gamma_eff)


def _py_spring_sand(z_m: float, D_m: float, phi_deg: float,
                    gamma_eff: float, y_ref: float) -> float:
    """Compute p at y_ref for sand -- GeoJm or local fallback."""
    result = get_py_reese(z_m=z_m, D_m=D_m, phi_deg=phi_deg)
    if result is not None:
        import numpy as np
        p_arr, y_arr = result
        return float(np.interp(y_ref, y_arr, p_arr))
    from ..analysis.pile_lateral import py_reese_sand
    return py_reese_sand(y_m=y_ref, depth_m=z_m, pile_D_m=D_m,
                         phi_deg=phi_deg, gamma_eff_kN_m3=gamma_eff)


def get_mander_concrete_from_geojm(
    fc: float,
    fyh: float,
    rho_s: float,
    b_core_mm: float = 400.0,
    h_core_mm: float = 400.0,
    s_mm: float = 100.0,
) -> ManderConfinedConcrete:
    """Return Mander confined concrete properties (fcc, eps_cc, eps_cu).

    Tries GeoJm first; falls back to the closed-form Mander (1988)
    equations if GeoJm is not installed.

    Args:
        fc: unconfined compressive strength (MPa).
        fyh: yield strength of transverse reinforcement (MPa).
        rho_s: volumetric ratio of transverse reinforcement.
        b_core_mm: core width (mm), centre-to-centre of ties.
        h_core_mm: core depth (mm), centre-to-centre of ties.
        s_mm: spacing of transverse reinforcement (mm).

    Returns:
        ``ManderConfinedConcrete(fcc, eps_cc, eps_cu)``.
    """
    rho_x = rho_s / 2.0
    rho_y = rho_s / 2.0
    result = get_mander_material(
        fc=fc, fyh=fyh, rho_x=rho_x, rho_y=rho_y,
        b_core_mm=b_core_mm, h_core_mm=h_core_mm, s_mm=s_mm,
    )
    if result is not None:
        # GeoJm uses fcc_MPa; fallback to fcc if present
        _fcc = getattr(result, "fcc_MPa", None) or getattr(result, "fcc", None) or fc
        _eps_cc = getattr(result, "eps_cc", None) or 0.002
        _eps_cu = getattr(result, "eps_cu", None) or 0.004
        return ManderConfinedConcrete(fcc=_fcc, eps_cc=_eps_cc, eps_cu=_eps_cu)

    # --- Closed-form Mander (1988) fallback ---
    # Confinement effectiveness coefficient
    ke = _mander_ke(b_core_mm, h_core_mm, s_mm, rho_s)
    # Effective lateral confining pressure
    fl_prime = ke * rho_s * fyh
    ratio = fl_prime / fc
    # Confined strength
    fcc = fc * (2.254 * math.sqrt(1 + 7.94 * ratio) - 2 * ratio - 1.254)
    # Confined strain at peak
    eps_c0 = 0.002
    eps_cc = eps_c0 * (1 + 5 * (fcc / fc - 1))
    # Ultimate confined strain (Paulay & Priestley 1992 approximation)
    eps_cu = 0.004 + 1.4 * rho_s * fyh * 0.1 / fcc
    return ManderConfinedConcrete(fcc=fcc, eps_cc=eps_cc, eps_cu=eps_cu)


def _mander_ke(b_core: float, h_core: float, s: float,
               rho_s: float) -> float:
    """Confinement effectiveness coefficient for rectangular sections."""
    # Simplified: ke = (1 - s'/(2*b_c)) * (1 - s'/(2*h_c)) / (1 - rho_cc)
    s_prime = s * 0.85  # clear spacing approx
    rho_cc = min(rho_s, 0.08)  # longitudinal steel ratio bound
    num = (1 - s_prime / (2 * b_core)) * (1 - s_prime / (2 * h_core))
    den = 1 - rho_cc
    return max(min(num / den, 1.0), 0.1)


__all__ = [
    "get_py_matlock", "get_py_reese",
    "get_mander_material", "get_pile_group_efficiency",
    "get_py_springs_from_geojm", "get_mander_concrete_from_geojm",
    "PYSpring", "ManderConfinedConcrete", "PileLayerData",
]
