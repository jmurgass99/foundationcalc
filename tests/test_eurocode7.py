"""Tests for codes/eurocode7.py — partial factors and design approaches."""

import pytest

from foundationcalc.codes.eurocode7 import (
    DesignApproach,
    LimitState,
    NationalAnnex,
    get_partial_factors,
    utilization_ratio,
)


def test_DA1_C1_factors():
    pf = get_partial_factors(DesignApproach.DA1_C1, LimitState.GEO)
    assert pf.actions.gamma_G_unfav == 1.35
    assert pf.actions.gamma_Q_unfav == 1.50
    assert pf.soil.gamma_phi == 1.0
    assert pf.resistance.gamma_Rv == 1.0


def test_DA1_C2_factors():
    pf = get_partial_factors(DesignApproach.DA1_C2, LimitState.GEO)
    assert pf.actions.gamma_G_unfav == 1.00
    assert pf.actions.gamma_Q_unfav == 1.30
    assert pf.soil.gamma_phi == 1.25
    assert pf.soil.gamma_cu == 1.40
    assert pf.resistance.gamma_Rv == 1.0


def test_DA2_factors_default():
    pf = get_partial_factors(DesignApproach.DA2, LimitState.GEO)
    assert pf.actions.gamma_G_unfav == 1.35
    assert pf.soil.gamma_phi == 1.0
    assert pf.resistance.gamma_Rv == 1.4
    assert pf.resistance.gamma_Rh == 1.1


def test_DA2_spain_buildings_overrides_resistance():
    pf = get_partial_factors(
        DesignApproach.DA2,
        LimitState.GEO,
        annex=NationalAnnex.SPAIN,
        structure_type="building",
    )
    assert pf.resistance.gamma_Rv == 2.15
    assert pf.resistance.gamma_Rh == 1.10


def test_DA2_spain_other_structures():
    pf = get_partial_factors(
        DesignApproach.DA2,
        LimitState.GEO,
        annex=NationalAnnex.SPAIN,
        structure_type="other",
    )
    assert pf.resistance.gamma_Rv == 1.85


def test_DA3_factors():
    pf = get_partial_factors(DesignApproach.DA3, LimitState.GEO)
    assert pf.actions.gamma_G_unfav == 1.35
    assert pf.soil.gamma_phi == 1.25
    assert pf.resistance.gamma_Rv == 1.0


def test_EQU_factors():
    pf = get_partial_factors(DesignApproach.DA1_C1, LimitState.EQU)
    assert pf.actions.gamma_G_unfav == 1.10
    assert pf.actions.gamma_G_fav == 0.90
    assert pf.soil.gamma_phi == 1.25


def test_SLS_unity_factors():
    pf = get_partial_factors(DesignApproach.DA1_C1, LimitState.SLS)
    assert pf.actions.gamma_G_unfav == 1.0
    assert pf.soil.gamma_phi == 1.0
    assert pf.resistance.gamma_Rv == 1.0


def test_utilization():
    assert utilization_ratio(54.0, 100.0) == pytest.approx(0.54)
    with pytest.raises(ValueError):
        utilization_ratio(10.0, 0.0)
