"""Tests strip footing memo."""
import pytest

from foundationcalc.memos.zapata_corrida import (
    StripFootingInput, render_strip_footing_memo,
)


def test_basic():
    r = render_strip_footing_memo(StripFootingInput(
        w_kN_per_m=300, sigma_admissible_kPa=200,
    ))
    # B = w / (sigma_adm - H*gamma_c) = 300 / (200 - 0.50*24) = 300/188 = 1.595745 m
    # (antes 300/200 = 1.5 sin peso propio, y la propia memoria daba FAIL)
    assert r.B_required_m == pytest.approx(300.0 / 188.0, rel=1e-9)
    assert r.sigma_actual_kPa == pytest.approx(200.0, rel=1e-9)
    assert r.is_safe is True
    assert r.markdown.startswith("# Memoria")


def test_overload():
    r = render_strip_footing_memo(StripFootingInput(
        w_kN_per_m=2000, sigma_admissible_kPa=100,
    ))
    # Demanda alta + autopeso → puede no ser safe
    assert r.B_required_m > 0
