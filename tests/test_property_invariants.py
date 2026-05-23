"""Property-based tests de invariantes geotecnicas.

Usa hypothesis para generar casos aleatorios y verificar que se
cumplen propiedades fundamentales del diseno de cimentaciones.

Estos tests son la red de seguridad: si una formula se rompe para un
caso de borde no contemplado, hypothesis lo encuentra.
"""
from __future__ import annotations
import math

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st, assume, settings


pytestmark = [pytest.mark.property]


# -----------------------------------------------------------------------------
# Strategies - generan parametros fisicamente plausibles
# -----------------------------------------------------------------------------

valid_phi = st.floats(min_value=15.0, max_value=45.0)            # angulo friccion
valid_cohesion = st.floats(min_value=0.0, max_value=200.0)       # kPa
valid_gamma = st.floats(min_value=14.0, max_value=22.0)          # kN/m3
valid_depth = st.floats(min_value=0.5, max_value=5.0)            # m
valid_width = st.floats(min_value=1.0, max_value=5.0)            # m
valid_kh = st.floats(min_value=0.0, max_value=0.3)               # seismic coef


# -----------------------------------------------------------------------------
# Invariantes
# -----------------------------------------------------------------------------

@given(phi=valid_phi, c=valid_cohesion, gamma=valid_gamma,
        depth=valid_depth, width=valid_width)
@settings(max_examples=50, deadline=2000)
def test_bearing_capacity_is_positive(phi, c, gamma, depth, width):
    """qu siempre > 0 para suelo valido."""
    try:
        from foundationdesignjm.services.bearing import (
            SoilLayerSpec, BearingInput, bearing_capacity_multilayer,
        )
    except ImportError:
        pytest.skip("services.bearing no disponible")
    layers = (SoilLayerSpec(thickness=10.0, gamma=gamma, phi=phi, c=c),)
    res = bearing_capacity_multilayer(BearingInput(
        L_x=width, L_y=width, depth=depth, layers=layers,
    ))
    assert res.qu_kPa > 0, f"qu={res.qu_kPa} para phi={phi}, c={c}"
    assert res.qa_kPa > 0
    assert res.FS > 1.0


@given(phi=valid_phi, gamma=valid_gamma,
        depth=valid_depth, width=valid_width,
        kh1=valid_kh, kh2=valid_kh)
@settings(max_examples=30, deadline=3000)
def test_seismic_reduces_bearing(phi, gamma, depth, width, kh1, kh2):
    """qu sismico siempre <= qu estatico para mismo suelo."""
    assume(kh1 < kh2)
    try:
        from foundationdesignjm.services.bearing import (
            SoilLayerSpec, BearingInput, bearing_capacity_multilayer,
        )
    except ImportError:
        pytest.skip("services.bearing no disponible")
    layers = (SoilLayerSpec(thickness=10.0, gamma=gamma, phi=phi),)
    res_low = bearing_capacity_multilayer(
        BearingInput(L_x=width, L_y=width, depth=depth, layers=layers,
                      seismic_kh=kh1))
    res_high = bearing_capacity_multilayer(
        BearingInput(L_x=width, L_y=width, depth=depth, layers=layers,
                      seismic_kh=kh2))
    assert res_high.qu_kPa <= res_low.qu_kPa + 1e-6


@given(phi=st.floats(min_value=25.0, max_value=40.0),
        H=st.floats(min_value=2.0, max_value=8.0),
        gamma=valid_gamma,
        kh=st.floats(min_value=0.0, max_value=0.2))
@settings(max_examples=30, deadline=2000)
def test_mononobe_okabe_KAE_greater_than_static(phi, H, gamma, kh):
    """K_AE sismico siempre >= Ka estatico (Rankine)."""
    try:
        from foundationdesignjm.services.seismic import (
            MononobeOkabeInput, mononobe_okabe_thrust,
        )
    except ImportError:
        pytest.skip("services.seismic no disponible")
    Ka_static = math.tan(math.radians(45 - phi/2)) ** 2
    try:
        res = mononobe_okabe_thrust(MononobeOkabeInput(
            H=H, gamma=gamma, phi=phi, kh=kh,
        ))
    except ValueError:
        assume(False)
        return
    assert res.K_AE >= Ka_static * 0.99, \
        f"K_AE={res.K_AE} < Ka_static={Ka_static} para phi={phi}, kh={kh}"


@given(N=st.floats(min_value=100.0, max_value=5000.0),
        L=st.floats(min_value=1.5, max_value=4.0))
@settings(max_examples=30, deadline=2000)
def test_isolated_footing_pressure_average_consistent(N, L):
    """q_avg debe igualar N / Ag."""
    try:
        from foundationdesignjm.services.footings import (
            IsolatedFootingInput, design_isolated_footing,
        )
    except ImportError:
        pytest.skip("services.footings no disponible")
    inp = IsolatedFootingInput(L_x=L, L_y=L, thickness=0.6, N=N)
    res = design_isolated_footing(inp)
    if "q_avg" in res.pressures:
        expected = N / (L * L)
        assert abs(res.pressures["q_avg"] - expected) / expected < 0.05
