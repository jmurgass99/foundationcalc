"""Tests para foundationcalc.excavations (EN 1997-1 §12)."""
from __future__ import annotations

import math
import pytest

from foundationcalc.excavations import (
    apparent_earth_pressure,
    basal_heave_clay,
    strut_force,
    terzaghi_peck_heave,
)
from foundationcalc.exceptions import GeotechError


# ---------------------------------------------------------------------------
# Heave / basal heave
# ---------------------------------------------------------------------------
def test_terzaghi_peck_heave_strip_10m_clay():
    """Excavacion 10 m en arcilla cu=50 kPa, gamma=18 — zanja larga."""
    res = terzaghi_peck_heave(B=5.0, L=50.0, gamma=18.0, c_u=50.0, H=10.0)
    # FS = 5.14 * 50 / (18 * 10) = 257 / 180 = 1.4278
    assert res["Nc"] == pytest.approx(5.14, rel=1e-6)
    assert res["geometry"] == "strip"
    assert res["FS"] == pytest.approx(5.14 * 50.0 / (18.0 * 10.0), rel=1e-6)
    assert 1.4 < res["FS"] < 1.5


def test_terzaghi_peck_heave_rectangular():
    """Excavacion cuadrada B=L=10 m: Nc = 5.7*(1+0.2) = 6.84."""
    res = terzaghi_peck_heave(B=10.0, L=10.0, gamma=18.0, c_u=50.0, H=8.0)
    assert res["geometry"] == "rectangular"
    assert res["Nc"] == pytest.approx(5.7 * 1.2, rel=1e-6)
    expected_FS = 5.7 * 1.2 * 50.0 / (18.0 * 8.0)
    assert res["FS"] == pytest.approx(expected_FS, rel=1e-6)


def test_basal_heave_with_surcharge():
    """Sobrecarga reduce FS proporcionalmente."""
    base = basal_heave_clay(H=10.0, B=5.0, gamma=18.0, c_u=50.0)
    with_q = basal_heave_clay(
        H=10.0, B=5.0, gamma=18.0, c_u=50.0, q_surcharge=20.0
    )
    assert with_q["FS"] < base["FS"]
    assert with_q["FS"] == pytest.approx(5.14 * 50.0 / (18.0 * 10.0 + 20.0))


def test_cu_zero_raises():
    """Caso limite c_u=0 debe lanzar GeotechError."""
    with pytest.raises(GeotechError):
        terzaghi_peck_heave(B=5.0, L=50.0, gamma=18.0, c_u=0.0, H=10.0)
    with pytest.raises(GeotechError):
        basal_heave_clay(H=10.0, B=5.0, gamma=18.0, c_u=0.0)


def test_cu_negative_raises():
    with pytest.raises(GeotechError):
        basal_heave_clay(H=10.0, B=5.0, gamma=18.0, c_u=-10.0)


# ---------------------------------------------------------------------------
# Apparent earth pressure
# ---------------------------------------------------------------------------
def test_apparent_pressure_sand_envelope():
    """Arena: p = 0.65 * Ka * gamma * H, envolvente rectangular."""
    H, gamma, phi = 10.0, 18.0, 30.0
    Ka_expected = math.tan(math.radians(45.0 - phi / 2.0)) ** 2  # = 1/3
    res = apparent_earth_pressure(H=H, gamma=gamma, soil_type="sand", phi=phi)
    assert res["Ka"] == pytest.approx(Ka_expected, rel=1e-6)
    assert res["shape"] == "rectangular"
    p_expected = 0.65 * Ka_expected * gamma * H
    assert res["p_max"] == pytest.approx(p_expected, rel=1e-6)
    # Envolvente plana
    assert all(p == pytest.approx(p_expected) for _, p in res["envelope"])


def test_apparent_pressure_soft_clay():
    """Arcilla blanda: Ns > 4, envolvente reducida."""
    res = apparent_earth_pressure(
        H=15.0, gamma=18.0, c_u=25.0, soil_type="soft_clay"
    )
    Ns = 18.0 * 15.0 / 25.0  # = 10.8 > 4
    assert res["Ns"] == pytest.approx(Ns, rel=1e-6)
    Kp_exp = 1.0 - 0.4 * 4.0 * 25.0 / (18.0 * 15.0)
    assert res["Kp"] == pytest.approx(Kp_exp, rel=1e-6)
    assert res["p_max"] > 0


def test_apparent_pressure_stiff_clay_trapezoidal():
    res = apparent_earth_pressure(
        H=10.0, gamma=18.0, c_u=100.0, soil_type="stiff_clay"
    )
    assert res["shape"] == "trapezoidal"
    assert res["p_max"] == pytest.approx(0.3 * 18.0 * 10.0)
    # Envolvente comienza y termina en cero
    assert res["envelope"][0][1] == 0.0
    assert res["envelope"][-1][1] == 0.0


def test_apparent_pressure_invalid_soil_type():
    with pytest.raises(GeotechError):
        apparent_earth_pressure(H=10.0, gamma=18.0, soil_type="lava")


# ---------------------------------------------------------------------------
# Strut forces
# ---------------------------------------------------------------------------
def test_strut_force_three_struts_15m_wall():
    """3 puntales en pared 15 m, arena phi=32, comprobar suma == area total."""
    diag = apparent_earth_pressure(H=15.0, gamma=18.0, soil_type="sand", phi=32.0)
    levels = [3.0, 7.5, 12.0]
    struts = strut_force(diag, levels, spacing=1.0)
    assert len(struts) == 3
    total = sum(s["force"] for s in struts)
    # Area total bajo la envolvente rectangular = p_max * H
    expected_total = diag["p_max"] * 15.0
    assert total == pytest.approx(expected_total, rel=1e-9)
    # Particion tributaria correcta
    assert struts[0]["z_top"] == pytest.approx(0.0)
    assert struts[0]["z_bot"] == pytest.approx(0.5 * (3.0 + 7.5))
    assert struts[-1]["z_bot"] == pytest.approx(15.0)


def test_strut_force_scales_with_spacing():
    diag = apparent_earth_pressure(H=10.0, gamma=18.0, soil_type="sand", phi=30.0)
    s1 = strut_force(diag, [2.0, 5.0, 8.0], spacing=1.0)
    s2 = strut_force(diag, [2.0, 5.0, 8.0], spacing=3.0)
    for a, b in zip(s1, s2):
        assert b["force"] == pytest.approx(3.0 * a["force"], rel=1e-9)


def test_strut_force_invalid_levels():
    diag = apparent_earth_pressure(H=10.0, gamma=18.0, soil_type="sand", phi=30.0)
    with pytest.raises(GeotechError):
        strut_force(diag, [5.0, 3.0])  # no ordenado
    with pytest.raises(GeotechError):
        strut_force(diag, [])  # vacio
    with pytest.raises(GeotechError):
        strut_force(diag, [-1.0, 5.0])  # fuera de rango
