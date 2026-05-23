"""Tests for the DynamicsJm bridge.

These tests cover the parts of the bridge that work WITHOUT DynamicsJm
installed (impedance-to-springs conversion, Veletsos-Meek period
elongation). The end-to-end pipeline is exercised conditionally.
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

from foundationdesignjm.dynamics import rectangular_footing_impedance
from foundationdesignjm.integration.dynamicsjm_bridge import (
    DYNAMICSJM_AVAILABLE,
    impedance_to_springs,
    ssi_modified_period,
)


def test_impedance_to_springs_returns_six_keys():
    imp = rectangular_footing_impedance(B_m=3.0, L_m=3.0, G_MPa=40.0)
    springs = impedance_to_springs(imp)
    assert set(springs.keys()) == {
        "vertical", "horizontal_x", "horizontal_y",
        "rocking_x", "rocking_y", "torsion",
    }
    for v in springs.values():
        assert set(v.keys()) == {"K_static", "K_dyn", "C_dyn"}


def test_ssi_period_always_longer_than_fixed():
    """The Veletsos-Meek formula must produce T_ssi ≥ T_fixed."""
    imp = rectangular_footing_impedance(B_m=3.0, L_m=3.0, G_MPa=40.0)
    res = ssi_modified_period(
        T_fixed_s=0.40, m_struct_kg=50000,
        h_struct_m=3.0, impedance=imp,
    )
    assert res.T_ssi >= res.T_fixed
    assert res.period_elongation >= 1.0


def test_ssi_period_grows_for_softer_soil():
    """Lower G → softer foundation → larger T_ssi."""
    imp_stiff = rectangular_footing_impedance(B_m=3, L_m=3, G_MPa=200)
    imp_soft = rectangular_footing_impedance(B_m=3, L_m=3, G_MPa=10)
    r_stiff = ssi_modified_period(0.40, 50000, 3.0, imp_stiff)
    r_soft = ssi_modified_period(0.40, 50000, 3.0, imp_soft)
    assert r_soft.T_ssi > r_stiff.T_ssi


def test_ssi_damping_includes_radiation():
    """ζ_ssi should be ≥ ζ_fixed because radiation damping adds energy loss."""
    imp = rectangular_footing_impedance(B_m=3, L_m=3, G_MPa=40, frequency_Hz=2.0)
    res = ssi_modified_period(
        T_fixed_s=0.40, m_struct_kg=50000,
        h_struct_m=3.0, impedance=imp, zeta_fixed=0.05,
    )
    assert res.zeta_ssi >= res.zeta_fixed - 1e-6


def test_ssi_taller_building_has_more_period_elongation():
    """Taller structures (larger h) elongate the period more (rocking term)."""
    imp = rectangular_footing_impedance(B_m=3, L_m=3, G_MPa=40)
    short = ssi_modified_period(0.40, 50000, 3.0, imp)
    tall = ssi_modified_period(0.40, 50000, 12.0, imp)
    assert tall.period_elongation > short.period_elongation


def test_dynamicsjm_pipeline_requires_dynamicsjm():
    """Without DynamicsJm installed, the pipeline must raise."""
    if DYNAMICSJM_AVAILABLE:
        pytest.skip("DynamicsJm available — skipping fallback test")
    from foundationdesignjm.integration.dynamicsjm_bridge import (
        cpt_to_seismic_loss_pipeline,
    )
    from foundationdesignjm.analysis.cpt import CPTProfile, CPTReading
    from foundationdesignjm.core.geometry import RectangularFoundation
    cpt = CPTProfile(readings=[CPTReading(depth=1, q_c_MPa=10)])
    pad = RectangularFoundation(length=2500, width=2500, thickness=500,
                               embedment_depth=1000)
    with pytest.raises(ImportError):
        cpt_to_seismic_loss_pipeline(
            cpt=cpt, foundation=pad,
            building_mass_kg=50000, building_height_m=3.0,
            building_T_fixed_s=0.4,
            ground_motion_t_s=np.linspace(0, 1, 10),
            ground_motion_a_g=np.zeros(10),
        )


@pytest.mark.skipif(not DYNAMICSJM_AVAILABLE,
                    reason="Requires DynamicsJm on PYTHONPATH")
def test_full_pipeline_with_dynamicsjm():
    from foundationdesignjm.analysis.cpt import CPTProfile, CPTReading
    from foundationdesignjm.core.geometry import RectangularFoundation
    from foundationdesignjm.integration.dynamicsjm_bridge import (
        cpt_to_seismic_loss_pipeline,
    )
    readings = [CPTReading(depth=d, q_c_MPa=10.0, f_s_kPa=60)
                for d in [0.5, 1, 2, 3, 4, 6, 8, 12]]
    cpt = CPTProfile(readings=readings, water_table_depth_m=5.0)
    pad = RectangularFoundation(length=3000, width=3000, thickness=500,
                                embedment_depth=1500)
    t = np.linspace(0, 5, 500)
    ag = 0.3 * 9.81 * np.sin(2 * np.pi * 2.0 * t) * np.exp(-0.3 * t)
    res = cpt_to_seismic_loss_pipeline(
        cpt=cpt, foundation=pad,
        building_mass_kg=50000, building_height_m=3.0,
        building_T_fixed_s=0.40,
        ground_motion_t_s=t, ground_motion_a_g=ag,
    )
    assert res.peak_idr_fixed > 0
    assert res.loss_fixed_USD >= 0
    assert res.ssi_fixed.T_ssi >= res.ssi_fixed.T_fixed


@pytest.mark.skipif(not DYNAMICSJM_AVAILABLE,
                    reason="Requires DynamicsJm on PYTHONPATH")
def test_base_isolation_reduces_loss():
    from foundationdesignjm.analysis.cpt import CPTProfile, CPTReading
    from foundationdesignjm.core.geometry import RectangularFoundation
    from foundationdesignjm.integration.dynamicsjm_bridge import (
        cpt_to_seismic_loss_pipeline,
    )
    from dynamicsjm.control.base_isolation import BilinearIsolator

    readings = [CPTReading(depth=d, q_c_MPa=10.0, f_s_kPa=60)
                for d in [0.5, 1, 2, 3, 4, 6, 8]]
    cpt = CPTProfile(readings=readings, water_table_depth_m=5.0)
    pad = RectangularFoundation(length=3000, width=3000, thickness=500,
                                embedment_depth=1500)
    t = np.linspace(0, 5, 500)
    ag = 0.4 * 9.81 * np.sin(2 * np.pi * 1.8 * t) * np.exp(-0.25 * t)
    isolator = BilinearIsolator(k1=1e6, k2=0.1e6, q_y=50000, damping_ratio=0.10)
    res = cpt_to_seismic_loss_pipeline(
        cpt=cpt, foundation=pad,
        building_mass_kg=50000, building_height_m=3.0,
        building_T_fixed_s=0.40,
        ground_motion_t_s=t, ground_motion_a_g=ag,
        isolator=isolator,
    )
    # Isolation must REDUCE the superstructure IDR (and therefore loss)
    assert res.peak_idr_isolated < res.peak_idr_fixed
    assert res.loss_isolated_USD <= res.loss_fixed_USD
