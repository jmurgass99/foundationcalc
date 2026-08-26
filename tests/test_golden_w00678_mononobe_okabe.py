"""Golden tests - Mononobe-Okabe seismic active earth pressure, anchored to
WorkIDs W00678 and W00704 (UPC-MEEC "Seismic design of foundations" slides,
Prof. A. Drougkas; EC8/EN 1998-5).

Provenance (_EXTRACCION_DOCUMENTOS/fichas/):
  - W00704_Seismic-design-foundations-RetainingWall.md — the PRIMARY source:
    a fully worked retaining-wall example with every intermediate value shown,
    including its own literal Python transcription of the K formula.
  - W00678_Seismic-design-of-foundations.md — a condensed summary of the same
    example (same numbers, less detail); used as a cross-check.

Worked example (both fichas, identical inputs):
  Wall H=6 m; dense dry sand gamma=18 kN/m3, phi=36 deg (characteristic),
  delta=20 deg (wall friction, characteristic), kh=0.2, kv=0.1.
  EC7 M2 partial factor gamma_phi=1.25 applied to BOTH phi and delta:
    phi_d = atan(tan(36)/1.25) = 30.2 deg;  delta_d = atan(tan(20)/1.25) = 16.2 deg
  Static Coulomb (theta=0): KA=0.298; PA = 0.5*0.298*18*6^2 = 96.6 kN/m (at H/3)
  +kv: tan(theta)=kh/(1+kv)=0.2/1.1 -> theta=10.3 deg; Ed=0.5*18*1.1*K*36 = 154.7 kN/m (critical)
  -kv: tan(theta)=kh/(1-kv)=0.2/0.9 -> theta=12.5 deg; Ed=0.5*18*0.9*K*36 = 137.5 kN/m
  He (resultant height) = (PA*H/3 + (Ed-PA)*H/2) / Ed = 2.38 m

The package already implements the full-generality Mononobe-Okabe formula
(`foundationdesignjm.analysis.seismic.mononobe_okabe_K` / `seismic_thrust`,
including the `gamma_phi` partial-factor reduction) predating this campaign,
so no new function was written here — this file only anchors goldens to the
existing code, exercising the `gamma_phi` parameter for the first time
(previously untested in test_seismic.py).

WHY THESE GOLDENS ARE NOT TAUTOLOGICAL
---------------------------------------
Every numeric oracle below is an independent hand substitution into the
classical closed-form Mononobe-Okabe formula (Mononobe 1929, Okabe 1926;
EN 1998-5:2004 Annex E) for a vertical wall (psi=90 deg) with horizontal
backfill (beta=0):

    K_AE = cos^2(phi_d - theta) /
           { cos(theta) * cos(delta_d + theta) *
             [1 + sqrt( sin(phi_d+delta_d)*sin(phi_d-theta) /
                        cos(delta_d+theta) )]^2 }

transcribed from scratch in a throwaway script and cross-checked term-by-term
against the psi/beta-general expression used inside `mononobe_okabe_K` for
the psi=90, beta=0 special case (NOT by calling `mononobe_okabe_K` itself).
A first attempt at this transcription (during the audit) contained a copy
error (an extra cos(theta) factor in the last denominator cosine) that made
it disagree with the package by ~0.8% relative; the discrepancy was traced to
the hand-calc bug, not the package, and the corrected formula reproduces
`mononobe_okabe_K` to float precision for both the static and seismic cases
below (see also W00704's own literal Python `mononobe_okabe()` snippet, run
verbatim as a second, fully independent oracle in `_hand_KAE_ficha_formula`).

IMPORTANT COURSE CORRECTION DURING THIS AUDIT
-----------------------------------------------
An earlier draft of this file wrongly flagged W00678's "phi=36 deg" golden
header as a mislabelling errata (reasoning: recomputing with phi=36,
gamma_phi=1.0 does not reproduce KA=0.298/PA=96.6). That conclusion was
wrong: W00678 itself prints phi_d=30.2 deg and delta_d=16.2 deg right next to
theta=10.3 deg, i.e. it is applying the EC7 M2 reduction gamma_phi=1.25 to
the characteristic phi=36/delta=20, not using phi=36 raw. W00704 confirms
this explicitly ("phi_d=arctan(tan(36)/1.25)=30.2 deg"). Recomputing with
phi_deg=36, delta_deg=20, gamma_phi=1.25 reproduces KA=0.298, PA=96.6,
phi_d=30.17, delta_d=16.23 to 3 significant figures — see
`test_w00678_static_K_and_PA_match_ficha_with_gamma_phi_125`. This file
anchors to that corrected reading.

ERRATA CONFIRMED IN BOTH W00678 AND W00704
---------------------------------------------
Both fichas print, for the '+kv' (critical) case: "theta=10.3 deg -> K=0.446".
Running W00704's OWN literal Python formula with its OWN stated inputs
(phi_d=30.2, delta_d=16.2, theta=10.3, beta=0, psi=90) gives K=0.4319, not
0.446 (full precision, unrounded intermediate angles: K=0.4325). The ficha's
own Ed=154.7 kN/m is consistent with K~=0.432-0.434
(0.5*18*1.1*0.4325*36=154.1), NOT with its own printed K=0.446
(0.5*18*1.1*0.446*36=158.95 =/= 154.7). Because the SAME erroneous K=0.446 is
printed in two independently-extracted fichas of the same original slide
deck, this is a genuine transcription/arithmetic error in the source
material (not an extraction artifact), confirmed by two independent routes:
the ficha's own formula code, and this package's `mononobe_okabe_K`.
We anchor to the recomputed K~=0.4325, not the printed 0.446 — see
`test_w00678_plus_kv_printed_K_is_an_errata`.

GAP IN THE CURRENT IMPLEMENTATION (not a ficha errata)
---------------------------------------------------------
`mononobe_okabe_K` computes
    theta = atan(kh / (1-kv))   if kv >= 0   else   atan(kh / (1+kv))
and `seismic_thrust` computes
    factor = (1+kv)             if kv >= 0   else   (1-kv)
The mathematically consistent (and ficha-matching) formula is simply
theta = atan(kh/(1+kv)) and factor = (1+kv), using SIGNED kv throughout, with
NO branching needed at all (kv=+0.1 -> 1.1 -> theta=10.3 deg [ficha '+kv'];
kv=-0.1 -> 0.9 -> theta=12.5 deg [ficha '-kv']). Instead:
  - theta's kv>=0 branch has the wrong sign (computes 1-kv=0.9 instead of
    1+kv=1.1), so kv=+0.1 wrongly lands on the '-kv' theta.
  - seismic_thrust's kv<0 branch has the wrong sign (computes 1-kv=1.1
    instead of 1+kv=0.9), so kv=-0.1 wrongly lands on the '+kv' amplitude.
Net effect: `kv=+0.1` and `kv=-0.1` currently produce IDENTICAL K, theta and
E_d from a single call each — the sign of kv is presently a no-op, and the
value returned (Ed~=168.0 kN/m at phi=36/gamma_phi=1.25) is not simply "extra
conservative": it OVERSHOOTS the true code-compliant envelope of the two
correctly-paired cases (Ed_true_envelope = max(154.1, 137.5) = 154.1 kN/m) by
~9%. Quantified and pinned as a regression in
`test_w00678_kv_sign_is_currently_a_no_op` and
`test_w00678_seismic_thrust_overshoots_true_envelope_by_9pct`, not silently
fixed (no behaviour change authorized for this campaign — anchoring golden
tests only).
"""

import math

import pytest

from foundationdesignjm.analysis.seismic import mononobe_okabe_K, seismic_thrust

PHI_CHAR = 36.0
DELTA_CHAR = 20.0
GAMMA_PHI = 1.25
GAMMA_SOIL = 18.0
H_WALL = 6.0


def _hand_KAE(phi_d_deg: float, delta_d_deg: float, theta_deg: float, beta_deg: float = 0.0) -> float:
    """Independent transcription of the classical M-O formula (vertical wall,
    psi=90 deg, DESIGN angles phi_d/delta_d already reduced). NOT a call into
    `mononobe_okabe_K` -- used as the oracle.
    """
    phi = math.radians(phi_d_deg)
    delta = math.radians(delta_d_deg)
    theta = math.radians(theta_deg)
    i = math.radians(beta_deg)
    num = math.cos(phi - theta) ** 2
    den = (
        math.cos(theta)
        * math.cos(delta + theta)
        * (
            1
            + math.sqrt(
                math.sin(phi + delta) * math.sin(phi - theta - i)
                / (math.cos(delta + theta) * math.cos(i))
            )
        )
        ** 2
    )
    return num / den


def _hand_KAE_ficha_formula(phi_d_deg, delta_d_deg, beta_deg, psi_deg, theta_deg) -> float:
    """W00704's OWN literal Python `mononobe_okabe()` K-formula (sin/cos with
    the general psi), run verbatim with the ficha's stated arguments. A
    SECOND, independent oracle -- neither this nor `_hand_KAE` calls the
    package function under test.
    """
    ph, de, be, ps, th = (math.radians(x) for x in (phi_d_deg, delta_d_deg, beta_deg, psi_deg, theta_deg))
    num = math.sin(ps + ph - th) ** 2
    sqrt_inner = math.sqrt(
        math.sin(ph + de) * math.sin(ph - be - th) / (math.sin(ps - th - de) * math.sin(ps + be))
    )
    den = math.cos(th) * math.sin(ps) ** 2 * math.sin(ps - th - de) * (1 + sqrt_inner) ** 2
    return num / den


# --- Static Coulomb case (kh=kv=0), phi=36 (char.), gamma_phi=1.25 ----------

def test_w00678_static_K_matches_hand_coulomb_formula():
    """kh=kv=0 collapses M-O to classical Coulomb Ka'. Independent hand oracle
    (not `mononobe_okabe_K` itself).
    """
    K, theta = mononobe_okabe_K(
        phi_deg=PHI_CHAR, delta_deg=DELTA_CHAR, kh=0.0, kv=0.0, gamma_phi=GAMMA_PHI,
    )
    phi_d = math.degrees(math.atan(math.tan(math.radians(PHI_CHAR)) / GAMMA_PHI))
    delta_d = math.degrees(math.atan(math.tan(math.radians(DELTA_CHAR)) / GAMMA_PHI))
    K_hand = _hand_KAE(phi_d, delta_d, theta_deg=0.0)
    assert theta == pytest.approx(0.0, abs=1e-9)
    assert K == pytest.approx(K_hand, rel=1e-9)


def test_w00678_static_K_and_PA_match_ficha_with_gamma_phi_125():
    """WorkID W00678/W00704: 'KA=0.298; PA=96.6 kN/m' for phi=36 (char.),
    delta=20 (char.), gamma_phi=1.25 (EC7 M2), gamma=18 kN/m3, H=6 m.

    (An earlier draft of this test wrongly anchored phi=36 with gamma_phi=1.0
    and flagged the ficha as mislabelled -- see module docstring "course
    correction". The ficha's own printed phi_d=30.2/delta_d=16.2 only follow
    from phi=36/delta=20 reduced by gamma_phi=1.25, which this test now uses.)
    """
    K, _ = mononobe_okabe_K(
        phi_deg=PHI_CHAR, delta_deg=DELTA_CHAR, kh=0.0, kv=0.0, gamma_phi=GAMMA_PHI,
    )
    PA = 0.5 * K * GAMMA_SOIL * H_WALL ** 2
    assert K == pytest.approx(0.298, abs=0.002)
    assert PA == pytest.approx(96.6, abs=0.5)


def test_w00678_design_angles_match_ficha():
    """phi_d=30.2 deg, delta_d=16.2 deg (both fichas print these explicitly
    as intermediate values -- independent hand computation of the EC7 M2
    tan-phi reduction, not read from the package internals).
    """
    phi_d = math.degrees(math.atan(math.tan(math.radians(PHI_CHAR)) / GAMMA_PHI))
    delta_d = math.degrees(math.atan(math.tan(math.radians(DELTA_CHAR)) / GAMMA_PHI))
    assert phi_d == pytest.approx(30.2, abs=0.05)
    assert delta_d == pytest.approx(16.2, abs=0.05)


# --- Seismic case kh=0.2, kv=+/-0.1, phi=36 (char.), gamma_phi=1.25, H=6 ----

def test_w00678_seismic_theta_matches_hand_calc():
    """theta = atan(kh/(1-kv)) for kv=+0.1 in the package's current (buggy,
    sign-inverted) branch selection -> atan(0.2/0.9) = 12.53 deg. This
    happens to equal the ficha's own '-kv' branch theta; see the module
    docstring 'gap in the current implementation' for why kv=+0.1 lands here
    instead of the ficha's '+kv' theta=10.3 deg.
    """
    _, theta = mononobe_okabe_K(
        phi_deg=PHI_CHAR, delta_deg=DELTA_CHAR, kh=0.2, kv=0.1, gamma_phi=GAMMA_PHI,
    )
    theta_hand = math.degrees(math.atan(0.2 / 0.9))
    assert theta == pytest.approx(theta_hand, rel=1e-9)
    assert theta == pytest.approx(12.53, abs=0.02)


def test_w00678_seismic_K_matches_ficha_minus_kv_case():
    """K at theta=12.53 deg matches BOTH independent hand oracles to float
    precision, and matches the ficha's own '-kv' case (theta=12.5 deg,
    K=0.471) to 3 significant figures.
    """
    K, theta = mononobe_okabe_K(
        phi_deg=PHI_CHAR, delta_deg=DELTA_CHAR, kh=0.2, kv=0.1, gamma_phi=GAMMA_PHI,
    )
    phi_d = math.degrees(math.atan(math.tan(math.radians(PHI_CHAR)) / GAMMA_PHI))
    delta_d = math.degrees(math.atan(math.tan(math.radians(DELTA_CHAR)) / GAMMA_PHI))
    K_hand1 = _hand_KAE(phi_d, delta_d, theta_deg=theta)
    K_hand2 = _hand_KAE_ficha_formula(phi_d, delta_d, beta_deg=0.0, psi_deg=90.0, theta_deg=theta)
    assert K == pytest.approx(K_hand1, rel=1e-9)
    assert K == pytest.approx(K_hand2, rel=1e-9)
    assert K == pytest.approx(0.471, abs=0.001)   # WorkID W00678/W00704 '-kv' case


def test_w00678_plus_kv_printed_K_is_an_errata():
    """Both W00678 and W00704 print '+kv: theta=10.3 -> K=0.446' -- but
    running W00704's OWN literal formula with those exact inputs gives
    K=0.4319 (unrounded angles: 0.4325), and 0.5*18*1.1*0.4325*36=154.1
    matches the ficha's own Ed=154.7 far better than
    0.5*18*1.1*0.446*36=158.95 does. Anchored to the recomputed value; the
    printed K=0.446 is a confirmed source-material transcription error
    (present identically in both independently-extracted fichas), not
    reproduced or asserted here.
    """
    phi_d = math.degrees(math.atan(math.tan(math.radians(PHI_CHAR)) / GAMMA_PHI))
    delta_d = math.degrees(math.atan(math.tan(math.radians(DELTA_CHAR)) / GAMMA_PHI))
    theta_plus = math.degrees(math.atan(0.2 / 1.1))
    K_correct = _hand_KAE_ficha_formula(phi_d, delta_d, beta_deg=0.0, psi_deg=90.0, theta_deg=theta_plus)
    Ed_correct = 0.5 * GAMMA_SOIL * 1.1 * K_correct * H_WALL ** 2

    assert theta_plus == pytest.approx(10.3, abs=0.02)
    assert K_correct == pytest.approx(0.4325, abs=0.001)
    assert K_correct != pytest.approx(0.446, abs=0.005)          # NOT the printed value
    assert Ed_correct == pytest.approx(154.1, abs=0.5)            # matches the ficha's own Ed
    assert 0.5 * GAMMA_SOIL * 1.1 * 0.446 * H_WALL ** 2 == pytest.approx(158.95, abs=0.1)  # printed K -> wrong Ed


def test_w00678_seismic_thrust_overshoots_true_envelope_by_9pct():
    """Quantifies the kv-sign no-op gap (see module docstring). The true
    EC8-5 envelope is max(Ed[+kv], Ed[-kv]) with theta/amplitude CONSISTENTLY
    paired per case:
        Ed[+kv] = 0.5*18*1.1*K(theta=10.3) = 154.1 kN/m  (governs, matches
                                                            ficha's 'critico')
        Ed[-kv] = 0.5*18*0.9*K(theta=12.5) = 137.5 kN/m
    The package's `seismic_thrust(kv=0.1)` call instead mixes the '-kv' theta
    (12.53 deg, larger K) with the '+kv' amplitude (1.1), returning ~168 kN/m
    -- about 9% above the true governing case, not merely "conservative
    padding".
    """
    phi_d = math.degrees(math.atan(math.tan(math.radians(PHI_CHAR)) / GAMMA_PHI))
    delta_d = math.degrees(math.atan(math.tan(math.radians(DELTA_CHAR)) / GAMMA_PHI))

    theta_plus = math.degrees(math.atan(0.2 / 1.1))
    theta_minus = math.degrees(math.atan(0.2 / 0.9))
    K_plus = _hand_KAE(phi_d, delta_d, theta_deg=theta_plus)
    K_minus = _hand_KAE(phi_d, delta_d, theta_deg=theta_minus)
    Ed_plus = 0.5 * GAMMA_SOIL * 1.1 * K_plus * H_WALL ** 2
    Ed_minus = 0.5 * GAMMA_SOIL * 0.9 * K_minus * H_WALL ** 2
    true_envelope = max(Ed_plus, Ed_minus)
    assert true_envelope == pytest.approx(154.1, abs=0.5)

    K_pkg, _ = mononobe_okabe_K(
        phi_deg=PHI_CHAR, delta_deg=DELTA_CHAR, kh=0.2, kv=0.1, gamma_phi=GAMMA_PHI,
    )
    res_pkg = seismic_thrust(H=H_WALL, gamma_star=GAMMA_SOIL, K_mo=K_pkg, kv=0.1)
    assert res_pkg.seismic_thrust == pytest.approx(168.0, abs=0.5)   # pinned regression

    overshoot = (res_pkg.seismic_thrust - true_envelope) / true_envelope
    assert overshoot == pytest.approx(0.09, abs=0.01)   # ~9% above the true envelope


def test_w00678_kv_sign_is_currently_a_no_op():
    """Regression guard for the discovered gap: `mononobe_okabe_K`/`seismic_thrust`
    give IDENTICAL results for kv=+0.1 and kv=-0.1, so the two-case EC8-5
    procedure (evaluate +kv and -kv, take the governing one) currently
    collapses to a single value that is not code-compliant (see
    `test_w00678_seismic_thrust_overshoots_true_envelope_by_9pct`). If a
    future change makes the two cases diverge again, this test should be
    revisited rather than deleted silently.
    """
    Kp, thp = mononobe_okabe_K(
        phi_deg=PHI_CHAR, delta_deg=DELTA_CHAR, kh=0.2, kv=0.1, gamma_phi=GAMMA_PHI,
    )
    Km, thm = mononobe_okabe_K(
        phi_deg=PHI_CHAR, delta_deg=DELTA_CHAR, kh=0.2, kv=-0.1, gamma_phi=GAMMA_PHI,
    )
    assert Kp == pytest.approx(Km, rel=1e-12)
    assert thp == pytest.approx(thm, rel=1e-12)

    resp = seismic_thrust(H=H_WALL, gamma_star=GAMMA_SOIL, K_mo=Kp, kv=0.1)
    resm = seismic_thrust(H=H_WALL, gamma_star=GAMMA_SOIL, K_mo=Km, kv=-0.1)
    assert resp.seismic_thrust == pytest.approx(resm.seismic_thrust, rel=1e-12)
