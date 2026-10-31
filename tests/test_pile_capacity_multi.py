"""Tests pile capacity multi-código."""
import pytest

from foundationcalc.pile_capacity_multi import (
    PileCapacityInput, design_pile_capacity,
)


@pytest.fixture
def base():
    return PileCapacityInput(
        Q_shaft_ult_kN=500, Q_tip_ult_kN=800,
        pile_type="driven", geotechnical_risk="medium",
    )


def test_5_codes(base):
    for c in ("EU", "SG", "US", "CO", "AU"):
        r = design_pile_capacity(base, code=c)
        assert r.Q_design_kN > 0
        # Capacidad diseño < capacidad última (1300 kN)
        assert r.Q_design_kN < (base.Q_shaft_ult_kN + base.Q_tip_ult_kN)


def test_bored_mas_conservador_eu(base):
    bored_input = PileCapacityInput(
        **{**base.__dict__, "pile_type": "bored"}
    )
    a = design_pile_capacity(base, code="EU")
    b = design_pile_capacity(bored_input, code="EU")
    assert b.Q_design_kN < a.Q_design_kN


def test_au_high_risk_mas_conservador():
    low = PileCapacityInput(Q_shaft_ult_kN=500, Q_tip_ult_kN=800,
                              geotechnical_risk="low")
    high = PileCapacityInput(Q_shaft_ult_kN=500, Q_tip_ult_kN=800,
                               geotechnical_risk="high")
    a = design_pile_capacity(low, code="AU")
    b = design_pile_capacity(high, code="AU")
    assert b.Q_design_kN < a.Q_design_kN
