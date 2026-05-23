"""Tests strip footing memo."""
import pytest

from foundationdesignjm.memos.zapata_corrida import (
    StripFootingInput, render_strip_footing_memo,
)


def test_basic():
    r = render_strip_footing_memo(StripFootingInput(
        w_kN_per_m=300, sigma_admissible_kPa=200,
    ))
    assert r.B_required_m == pytest.approx(1.5, rel=1e-6)
    assert r.markdown.startswith("# Memoria")


def test_overload():
    r = render_strip_footing_memo(StripFootingInput(
        w_kN_per_m=2000, sigma_admissible_kPa=100,
    ))
    # Demanda alta + autopeso → puede no ser safe
    assert r.B_required_m > 0
