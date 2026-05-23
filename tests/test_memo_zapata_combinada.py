"""Tests memo zapata combinada."""
import pytest

from foundationdesignjm.memos.zapata_combinada import (
    CombinedFootingInput, render_combined_footing_memo,
)


def test_simetrica_sin_excentricidad():
    r = render_combined_footing_memo(CombinedFootingInput(
        P1_kN=500, P2_kN=500, distance_cols_m=4, L_m=6, B_m=2,
        sigma_admissible_kPa=200,
    ))
    assert abs(r.e_m) < 1e-6  # zapata centrada en la resultante
    assert r.sigma_max_kPa == pytest.approx(r.sigma_min_kPa, rel=1e-6)


def test_excentrica():
    r = render_combined_footing_memo(CombinedFootingInput(
        P1_kN=800, P2_kN=200, distance_cols_m=4, L_m=6, B_m=2,
    ))
    assert r.sigma_max_kPa > r.sigma_min_kPa


def test_overload_falla_admisible():
    r = render_combined_footing_memo(CombinedFootingInput(
        P1_kN=5000, P2_kN=5000, distance_cols_m=4, L_m=4, B_m=1,
    ))
    assert not r.is_safe_bearing
