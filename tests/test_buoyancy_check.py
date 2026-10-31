"""Tests for buoyancy_check."""
import pytest
from foundationcalc.design.buoyancy_check import (
    BuoyancyInput, check_buoyancy, required_ballast_kN,
)


def test_no_water_passes():
    r = check_buoyancy(BuoyancyInput(base_area_m2=20.0, submerged_depth_m=0.0,
                                     structure_weight_kN=500.0))
    assert r.uplift_force_kN == 0.0
    assert r.passes is True


def test_uplift_fails_when_light():
    inp = BuoyancyInput(base_area_m2=20.0, submerged_depth_m=3.0,
                        structure_weight_kN=100.0)
    r = check_buoyancy(inp)
    # U = 9.81*3*20 = 588.6 kN; W=100 -> FS<1
    assert r.uplift_force_kN == pytest.approx(588.6, rel=1e-3)
    assert r.passes is False
    assert r.factor_of_safety < 1.0


def test_multi_code_FS_requirements():
    inp = BuoyancyInput(base_area_m2=10.0, submerged_depth_m=2.0,
                        structure_weight_kN=300.0)
    for code in ("USA", "EU", "NSR", "AS", "SG"):
        r = check_buoyancy(BuoyancyInput(**{**inp.__dict__, "code": code}))
        assert r.required_FS > 0
    with pytest.raises(ValueError):
        check_buoyancy(BuoyancyInput(base_area_m2=1, submerged_depth_m=1,
                                     structure_weight_kN=10, code="ZZ"))


def test_required_ballast():
    inp = BuoyancyInput(base_area_m2=20.0, submerged_depth_m=3.0,
                        structure_weight_kN=200.0, code="USA")
    b = required_ballast_kN(inp)
    # FS req = 1.5 -> need 1.5*588.6 - 200 = 682.9 kN
    assert b == pytest.approx(682.9, rel=1e-2)


def test_invalid_inputs():
    with pytest.raises(ValueError):
        check_buoyancy(BuoyancyInput(base_area_m2=0, submerged_depth_m=1, structure_weight_kN=10))
    with pytest.raises(ValueError):
        check_buoyancy(BuoyancyInput(base_area_m2=10, submerged_depth_m=-1, structure_weight_kN=10))
