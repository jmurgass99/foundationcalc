"""Tests del modulo foundationcalc.memos."""
from __future__ import annotations
import pytest

handcalcs = pytest.importorskip("handcalcs")

from foundationcalc.memos import footing_ec7_bearing_memo


def test_footing_bearing_safe_case():
    """Zapata 2x2 m a 1.5 m de profundidad, suelo competente."""
    latex, res = footing_ec7_bearing_memo(
        B=2.0, L=2.0, D_f=1.5, gamma_soil=19.0,
        c=10.0, phi_deg=30.0, R_Ed=1000.0, gamma_R=1.4,
    )
    assert res.R_d_kN > 0
    assert res.sigma_ult_kPa > res.sigma_d_kPa
    assert res.N_q > 1 and res.N_c > 1
    assert "\\" in latex


def test_footing_bearing_fails_for_high_load():
    """Carga excesiva: no cumple."""
    _, res = footing_ec7_bearing_memo(
        B=1.0, L=1.0, D_f=0.5, gamma_soil=18.0,
        c=0.0, phi_deg=20.0, R_Ed=1000.0, gamma_R=1.4,
    )
    assert not res.is_safe
    assert res.R_d_kN < 1000.0


def test_footing_bearing_phi_zero_uses_cohesion():
    """phi=0 (arcilla pura): R debe venir solo de cohesion."""
    _, res = footing_ec7_bearing_memo(
        B=2.0, L=2.0, D_f=1.0, gamma_soil=18.0,
        c=50.0, phi_deg=0.1, R_Ed=500.0, gamma_R=1.4,
    )
    assert res.R_d_kN > 0
    assert res.N_q < 2  # phi=0.1 deg -> N_q ~ 1


def test_footing_bearing_invalid_inputs():
    with pytest.raises(ValueError):
        footing_ec7_bearing_memo(B=-1, L=2, D_f=1, gamma_soil=18, c=0, phi_deg=30, R_Ed=100)
    with pytest.raises(ValueError):
        footing_ec7_bearing_memo(B=2, L=1, D_f=1, gamma_soil=18, c=0, phi_deg=30, R_Ed=100)  # L < B
    with pytest.raises(ValueError):
        footing_ec7_bearing_memo(B=2, L=2, D_f=1, gamma_soil=18, c=0, phi_deg=50, R_Ed=100)  # phi >= 50


def test_footing_larger_means_more_capacity():
    _, r1 = footing_ec7_bearing_memo(B=1, L=1, D_f=1, gamma_soil=18, c=10, phi_deg=30, R_Ed=100)
    _, r2 = footing_ec7_bearing_memo(B=2, L=2, D_f=1, gamma_soil=18, c=10, phi_deg=30, R_Ed=100)
    assert r2.R_d_kN > r1.R_d_kN
