"""Golden tests — bearing-capacity factors and drained capacity anchored to
worked geotechnical examples (UPC MEEC, SEM1 Foundation Structures).

Provenance (WorkIDs, _EXTRACCION_DOCUMENTOS):
  - W00675  "Examples of geotechnical design according to Eurocode 7"
            (EC7 worked slides). Carries an explicit tabulated set of bearing-
            capacity factors N_q / N_c / N_gamma vs phi' (5 values) plus two
            fully worked q_ult calculations (Examples 1 & 2).
  - W00681  "Shallow Foundations Example 2025" — strip footing EC7-DA2,
            phi'=30, qult=1072 kPa.

Eurocode clause: EN 1997-1:2004 Annex D (D.3/D.4) — drained bearing resistance
  R/A' = c'·N_c·s_c·... + q'·N_q·s_q·... + 0.5·gamma'·B'·N_gamma·s_gamma·...
with
  N_q     = e^(pi·tan phi') · tan^2(45 + phi'/2)     (author-independent)
  N_c     = (N_q - 1)·cot phi'                        (author-independent)
  N_gamma : author-dependent.

WHY THESE GOLDENS ARE NOT TAUTOLOGICAL
--------------------------------------
1. N_q and N_c are hard-anchored to the W00675 table literals. Their closed
   form is identical across every author (Brinch-Hansen / Meyerhof / Vesic /
   Chen-EC7), so the table is a genuine *independent* oracle: any correct
   implementation must reproduce 10.66 / 20.72 (phi=25) ... 33.30 / 46.12
   (phi=35) regardless of internal formula choice.

2. N_gamma anchors to the W00675 *table literals* (hardcoded numbers from an
   independent hand-calc source, not recomputed here). Auditing the table
   exposed a labelling errata in the ficha (see below): despite being headed
   "Hansen / EN 1997-1 Annex D", the tabulated N_gamma is in fact the **Vesic**
   form  N_gamma = 2·(N_q + 1)·tan phi'  (e.g. 48.03 at phi=35), NOT the
   Annex-D / Chen form 2·(N_q - 1)·tan phi' (= 45.23 at phi=35, which the
   package default `CHEN_EC7` already produces and which is covered by the
   existing test_bearing_capacity.py::test_bearing_factors_phi_35). We anchor
   the Vesic branch to the table and keep the Annex-D branch where it belongs.
   This is exactly the "fichas pueden traer erratas -> manda el cálculo
   honesto" pattern from PLAN_DETALLADO.md §6.

3. The drained-capacity integration golden (W00675 Example 2) is anchored to
   the *ficha's three hand-computed q_ult components* (258.0 / 397.4 / 167.2
   kPa), an independently summed result (822.6 kPa), not to a re-run of the
   engine. A plane-strain strip (B'/L' -> 0, shape factors -> 1.0) is used so
   the comparison is term-by-term faithful to the hand calc, and it exercises
   the c'·N_c cohesion term that the existing sand-only (c'=0) goldens omit.
"""

import math

import pytest

from foundationcalc.analysis.bearing_capacity import (
    BearingCapacityFormula,
    bearing_capacity_factors,
    drained_bearing_capacity,
)
from foundationcalc.core.geometry import FootingType, RectangularFoundation
from foundationcalc.core.soil import SoilLayer, SoilType


# --- W00675 tabulated bearing-capacity factors (phi -> Nq, Nc, Ngamma) -------
# Headed "Hansen / EN 1997-1 Annex D" in the ficha, but Ngamma is Vesic
# 2(Nq+1)tan phi (verified term-by-term against the closed forms).
W00675_FACTOR_TABLE = {
    25: (10.66, 20.72, 10.88),
    28: (14.72, 25.80, 16.72),
    30: (18.40, 30.14, 22.40),
    32: (23.18, 35.49, 30.22),
    35: (33.30, 46.12, 48.03),
}


@pytest.mark.parametrize("phi_deg", sorted(W00675_FACTOR_TABLE))
def test_w00675_Nq_Nc_author_independent(phi_deg):
    """N_q and N_c match the W00675 table for every phi' (author-independent).

    EN 1997-1 Annex D — N_q = e^(pi tan phi) tan^2(45+phi/2), N_c = (Nq-1)cot phi.
    Anchored to independent hand-calc literals (WorkID W00675).
    """
    Nq_t, Nc_t, _ = W00675_FACTOR_TABLE[phi_deg]
    Nq, Nc, _ = bearing_capacity_factors(phi_deg, BearingCapacityFormula.CHEN_EC7)
    assert Nq == pytest.approx(Nq_t, abs=0.02)
    assert Nc == pytest.approx(Nc_t, abs=0.02)


@pytest.mark.parametrize("phi_deg", sorted(W00675_FACTOR_TABLE))
def test_w00675_Ngamma_is_vesic(phi_deg):
    """The W00675-tabulated N_gamma is the Vesic form 2(Nq+1)tan phi'.

    Anchored to the table literals (WorkID W00675). Documents the ficha
    labelling errata: the table header says "Hansen/Annex D" but the numbers
    are Vesic.
    """
    _, _, Ng_t = W00675_FACTOR_TABLE[phi_deg]
    _, _, Ng_vesic = bearing_capacity_factors(phi_deg, BearingCapacityFormula.VESIC)
    assert Ng_vesic == pytest.approx(Ng_t, abs=0.02)


def test_w00675_Ngamma_table_is_not_annexD_chen():
    """Guard the errata finding: the table N_gamma is NOT the Annex-D/Chen form.

    Chen-EC7 N_gamma = 2(Nq-1)tan phi' = 45.23 at phi=35, which differs from the
    table's 48.03 by >2.5. This pins the distinction so a future "simplify"
    cannot silently collapse the two branches.
    """
    _, _, Ng_chen = bearing_capacity_factors(35.0, BearingCapacityFormula.CHEN_EC7)
    assert Ng_chen == pytest.approx(45.23, abs=0.05)
    assert abs(Ng_chen - W00675_FACTOR_TABLE[35][2]) > 2.5


# --- W00675 Example 2: strip footing, drained, with cohesion -----------------
#   phi'=28, c'=10 kPa, gamma'=10 kN/m3 (below WT), overburden q'=27 kPa, B=2 m.
#   Hand-calc (Vesic Ngamma, strip => shape factors = 1.0):
#     q_ult = c'·Nc + q'·Nq + 0.5·gamma'·B·Ngamma
#           = 10·25.80 + 27·14.72 + 0.5·10·2·16.72
#           = 258.0 + 397.4 + 167.2 = 822.6 kPa
# A 10 km-long strip drives B'/L' -> 0 so the engine's shape factors collapse to
# 1.0 and the term-by-term comparison is faithful to the hand calc.
def _w00675_ex2_result():
    strip = RectangularFoundation(
        length=10_000_000.0,  # plane-strain strip: B'/L' -> 0 => s_* -> 1.0
        width=2000.0,
        thickness=500.0,
        embedment_depth=1000.0,
        footing_type=FootingType.STRIP,
    )
    soil = SoilLayer(
        name="sand_below_WT",
        thickness=10.0,
        soil_type=SoilType.MIXED,
        friction_angle=28.0,
        cohesion=10.0,
        unit_weight=10.0,  # gamma' = gamma_sat - gamma_w
    )
    return drained_bearing_capacity(
        foundation=strip,
        soil=soil,
        overburden_pressure=27.0,
        formula=BearingCapacityFormula.VESIC,
        use_inclination=False,
    )


def test_w00675_ex2_factors_match_table():
    res = _w00675_ex2_result()
    Nq_t, Nc_t, Ng_t = W00675_FACTOR_TABLE[28]
    assert res.Nq == pytest.approx(Nq_t, abs=0.02)
    assert res.Nc == pytest.approx(Nc_t, abs=0.02)
    assert res.Ngamma == pytest.approx(Ng_t, abs=0.02)


def test_w00675_ex2_shape_factors_collapse_to_unity():
    """Sanity: the plane-strain strip yields strip shape factors (~1.0)."""
    res = _w00675_ex2_result()
    assert res.sq == pytest.approx(1.0, abs=1e-3)
    assert res.sc == pytest.approx(1.0, abs=1e-3)
    assert res.sgamma == pytest.approx(1.0, abs=1e-3)


def test_w00675_ex2_qult_components():
    """Each q_ult term matches the W00675 Example 2 hand calc (kPa)."""
    res = _w00675_ex2_result()
    assert res.q_ult_cohesion == pytest.approx(258.0, abs=1.0)      # c'·Nc
    assert res.q_ult_overburden == pytest.approx(397.4, abs=1.0)    # q'·Nq
    assert res.q_ult_self_weight == pytest.approx(167.2, abs=1.0)   # 0.5 gamma' B Ngamma


def test_w00675_ex2_qult_total():
    """Total drained bearing resistance q_ult = 822.6 kPa (WorkID W00675 Ex.2)."""
    res = _w00675_ex2_result()
    assert res.q_ult == pytest.approx(822.6, abs=1.5)


# --- W00681 strip footing: q_ult breakdown (depth factor documented) ---------
#   phi'=30, c'=0, gamma=18, Df=1.0 m (overburden q'=27 kPa), B=2.5 m.
#   The ficha reports q_ult=1072 kPa using a depth factor dq=1.138 on the
#   overburden term (568 = 27·18.4·1.138). The package `drained_bearing_capacity`
#   does NOT apply depth factors, so the engine returns ~1003 kPa. We anchor the
#   *self-weight* term (depth-factor-free) to the ficha and pin the no-dq total,
#   documenting the gap rather than masking it.
def _w00681_result():
    strip = RectangularFoundation(
        length=10_000_000.0,
        width=2500.0,
        thickness=500.0,
        embedment_depth=1000.0,
        footing_type=FootingType.STRIP,
    )
    soil = SoilLayer(
        name="sand",
        thickness=10.0,
        soil_type=SoilType.COHESIONLESS,
        friction_angle=30.0,
        cohesion=0.0,
        unit_weight=18.0,
    )
    return drained_bearing_capacity(
        foundation=strip,
        soil=soil,
        overburden_pressure=27.0,
        formula=BearingCapacityFormula.VESIC,
        use_inclination=False,
    )


def test_w00681_self_weight_term_matches_ficha():
    """Self-weight term 0.5 gamma B Ngamma = 504 kPa (no depth factor involved).

    Ficha W00681: 0.5·18·2.5·22.40 = 504 kPa.
    """
    res = _w00681_result()
    assert res.q_ult_self_weight == pytest.approx(504.0, abs=1.5)


def test_w00681_overburden_term_no_depth_factor():
    """Engine overburden term is the depth-factor-FREE value q'·Nq = 27·18.40.

    Documents that `drained_bearing_capacity` omits the EN 1997-1 depth factors:
    the ficha's 568 kPa includes dq=1.138; the engine returns 496.8 kPa.
    """
    res = _w00681_result()
    assert res.q_ult_overburden == pytest.approx(27.0 * 18.40, abs=1.0)  # 496.8, no dq


def test_w00681_qult_total_without_depth_factor():
    """No-depth-factor total ~1001 kPa (vs ficha 1072 with dq). Regression pin."""
    res = _w00681_result()
    # 496.8 (q-term, no dq) + 504.3 (g-term) ~ 1001 kPa
    assert res.q_ult == pytest.approx(1001.0, abs=4.0)
    assert res.q_ult < 1072.0  # strictly below the with-depth-factor ficha value
