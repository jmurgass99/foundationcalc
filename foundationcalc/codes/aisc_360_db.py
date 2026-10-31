"""Closed-form derivation of doubly-symmetric I-shape properties.

Pulls (h, b, tw, tf) tuples from `fastsap.section_catalog` (EU + US) and
computes the derived properties needed by `aisc_360.SteelShape`. Outputs
are in SI base for the existing aisc_360 module: mm, mm², mm³, mm⁴.

For published values that include fillet effects, override fields after
calling `SteelShape.from_aisc(...)`. The closed-form (sharp-corner)
properties typically agree with the published tables to within 3-5 % for
A and Ix.
"""
from __future__ import annotations

from math import sqrt

from ..section_catalog import _ALL


def aisc_w_properties(name: str) -> dict:
    """Return a dict of closed-form I-shape properties (mm, mm², mm³, mm⁴).

    Keys:
        d, bf, tw, tf  — geometry (mm)
        A              — gross area (mm²)
        Ix, Iy         — second moments about centroidal axes (mm⁴)
        Sx, Sy         — elastic section moduli (mm³)
        Zx, Zy         — plastic section moduli (mm³)
        rx, ry         — radii of gyration (mm)
        J              — torsion constant (thin-walled open) Σ b·t³/3 (mm⁴)
        Cw             — warping constant Iy·(d − tf)² / 4 (mm⁶)
        h0             — distance between flange centroids (mm)

    Raises:
        KeyError if `name` is not in the EU+US catalog.
    """
    if name not in _ALL:
        raise KeyError(
            f"Section '{name}' not in catalog. "
            f"First entries: {sorted(_ALL)[:5]}…"
        )
    d_m, bf_m, tw_m, tf_m = _ALL[name]
    d = d_m * 1000.0
    bf = bf_m * 1000.0
    tw = tw_m * 1000.0
    tf = tf_m * 1000.0
    h_w = d - 2.0 * tf                                          # clear web height
    A = 2.0 * bf * tf + h_w * tw
    Ix = (bf * d ** 3 - (bf - tw) * h_w ** 3) / 12.0
    Iy = (2.0 * tf * bf ** 3 + h_w * tw ** 3) / 12.0
    Sx = 2.0 * Ix / d
    Sy = 2.0 * Iy / bf
    Zx = bf * tf * (d - tf) + tw * h_w ** 2 / 4.0
    Zy = 2.0 * (tf * bf ** 2 / 4.0) + (h_w * tw ** 2) / 4.0
    rx = sqrt(Ix / A)
    ry = sqrt(Iy / A)
    J = (2.0 * bf * tf ** 3 + h_w * tw ** 3) / 3.0
    h0 = d - tf
    Cw = Iy * h0 ** 2 / 4.0
    return {
        "d": d, "bf": bf, "tw": tw, "tf": tf,
        "A": A, "Ix": Ix, "Iy": Iy, "Sx": Sx, "Sy": Sy,
        "Zx": Zx, "Zy": Zy, "rx": rx, "ry": ry,
        "J": J, "Cw": Cw, "h0": h0,
    }


__all__ = ["aisc_w_properties"]
