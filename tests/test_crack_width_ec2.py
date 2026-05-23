"""Tests EN 1992-1-1 §7.3 crack width."""
import pytest

from foundationdesignjm.crack_width_ec2 import CrackWidthInput, crack_width_EC2


def test_caso_estandar_within_limit():
    r = crack_width_EC2(CrackWidthInput(
        bar_diameter_mm=16, cover_mm=40, sigma_s_MPa=180,
    ))
    # σ_s baja → wk pequeño
    assert r.wk_mm < 0.5


def test_alta_tension_aumenta_wk():
    r1 = crack_width_EC2(CrackWidthInput(
        bar_diameter_mm=20, cover_mm=40, sigma_s_MPa=150,
    ))
    r2 = crack_width_EC2(CrackWidthInput(
        bar_diameter_mm=20, cover_mm=40, sigma_s_MPa=350,
    ))
    assert r2.wk_mm > r1.wk_mm


def test_rho_alto_reduce_sr_max():
    rho_bajo = crack_width_EC2(CrackWidthInput(
        bar_diameter_mm=16, cover_mm=40, rho_p_eff=0.01,
    ))
    rho_alto = crack_width_EC2(CrackWidthInput(
        bar_diameter_mm=16, cover_mm=40, rho_p_eff=0.05,
    ))
    assert rho_alto.sr_max_mm < rho_bajo.sr_max_mm
