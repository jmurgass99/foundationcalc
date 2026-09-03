"""`aci318_anchorage.shear_capacity`: flat 0.60 steel shear + declared scope.

Third of the three ACI-17 anchorage twins in this monorepo. The defect was
fixed first in ``fastsap.codes.anchorage`` (see
``packages/fastsap/tests/test_anchorage_absence_and_steel_shear.py``), which
turned out to have zero production importers; this module is reached through
``foundationdesignjm.codes.__init__`` as the public ``aci_anchor_shear``.

The steel term is ``Vsa = 0.6 * n_anchors * Ase_V * futa`` — ACI 318-19
§17.7.1.2 **case (b)** only, under a comment that said no more than
``# Steel (17.7.1.2)``.

This module's own docstring scopes it to *cast-in headed anchors*, which
changes its gap list relative to the fastsap twin: case (c) sleeved
post-installed anchors are outside the advertised scope here, while welded
headed studs are squarely **inside** it — a welded stud is a cast-in headed
anchor — and are charged the conservative 0.60 because no argument tells
them from a headed bolt.

Nothing here is a *golden* value: no independent hand-calculation or
code-published example is reproduced. These are **characterization +
decision-pinning** tests. The 0.60 is read off §17.7.1.2(b) via secondary
sources; the assertions below pin this module's declared scope and the two
decisions taken, not a code-published result.

Both omissions were considered and deliberately left as documented
limitations rather than becoming inputs:

- the **grout-pad 0.80 multiplier** — its ACI 318-19 clause number and its
  value could not be verified against the printed standard, so a
  ``grout_pad=True`` argument would ship an unverifiable number;
- the **futa cap** min(1.9·fya, 860 MPa) — enforcing it means adding
  ``fya`` to a public signature, and ``tension_capacity`` states the cap as
  a caller precondition without enforcing it either.

**Why the scope test keys on block *headers*, not on bare tokens.** A first
version looked for ``"futa"``/``"stud"`` anywhere in the docstring. Both
words occur in the Args list, the formula and the sourcing note, so
mutations that deleted the whole ``**futa cap**`` and ``**Not covered —
case (a)**`` blocks passed unnoticed. Each limitation must own a bold
header line that names its concept.
"""
from __future__ import annotations

import ast
import inspect
import pathlib

import pytest

from foundationdesignjm.codes import aci318_anchorage, aci_anchor_shear
from foundationdesignjm.codes.aci318_anchorage import shear_capacity


BASE = dict(Ase_V=157.0, futa=400.0, fc=28.0, hef=200.0, ca1=300.0, da=16.0)


def _bold_headers(doc: str) -> list[str]:
    """Lines that open a bold declaration block, e.g. ``**Not covered — ...``."""
    return [ln.strip() for ln in doc.splitlines() if ln.strip().startswith("**")]


# ---------------------------------------------------------------------------
# 1. The steel term is a flat 0.60 with nothing hidden inside it
# ---------------------------------------------------------------------------

def test_shear_steel_is_exactly_0p60_with_no_hidden_multiplier():
    """Vsa must be 0.60·n·Ase_V·futa exactly.

    This pins the *decision* that the declined grout-pad 0.80 multiplier
    stays declared-but-unapplied. If someone later wires 0.80 in as a
    default rather than as an explicit input, Vsa silently drops by 20%
    and this catches it.
    """
    r = shear_capacity(Vu=1.0, n_anchors=2, **BASE)
    assert r.Vsa == pytest.approx(0.60 * 2 * 157.0 * 400.0, rel=1e-12)


def test_cracked_flag_does_not_touch_the_steel_term():
    """``cracked`` is the only bool in the signature and it is a *concrete*
    property. Steel shear must not move with it — otherwise the module
    would fake a distinction §17.7.1.2 does not draw along that axis, the
    defect this file exists to prevent."""
    cracked = shear_capacity(Vu=1.0, cracked=True, **BASE)
    uncracked = shear_capacity(Vu=1.0, cracked=False, **BASE)
    assert cracked.Vsa == uncracked.Vsa


def test_futa_cap_is_declared_but_deliberately_not_enforced():
    """Characterization of an accepted, declared limitation.

    ACI caps futa at min(1.9·fya, 860 MPa). This function receives no fya
    and applies no cap, so Vsa keeps scaling linearly past 860 MPa. That is
    unconservative and it is *documented as such*; the test pins the
    behaviour so the limitation cannot be quietly dropped from the
    docstring while staying real in the code.
    """
    r = shear_capacity(Vu=1.0, **dict(BASE, futa=1200.0))
    assert r.Vsa == pytest.approx(0.60 * 1 * 157.0 * 1200.0, rel=1e-12), (
        "futa appears to be capped now — if that is intended, the docstring "
        "limitation must be replaced by a stated cap and an fya argument"
    )


# ---------------------------------------------------------------------------
# 2. No conditional may fake a distinction it does not make
# ---------------------------------------------------------------------------

def _identical_branch_conditionals(source: str) -> list[tuple[int, str]]:
    """Return (lineno, dumped node) for every `a if c else b` with a == b.

    Only constant branches are compared: two identical literals are a fake
    distinction with certainty, whereas two identical expressions could
    still be a deliberate (if redundant) call.
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.IfExp):
            continue
        body, orelse = node.body, node.orelse
        if (isinstance(body, ast.Constant) and isinstance(orelse, ast.Constant)
                and type(body.value) is type(orelse.value)
                and body.value == orelse.value):
            found.append((node.lineno, ast.unparse(node)))
    return found


def test_module_has_no_conditional_with_identical_branches():
    """Ported from ``test_anchorage_absence_and_steel_shear.py``.

    The original defect was ``factor = 0.60 if anchor.cast_in else 0.60`` —
    a ternary whose branches are the same literal, claiming a distinction
    the code does not make. This module never had that exact line; the
    guard is what stops it being *introduced*. A mutation writing
    ``(0.6 if cracked else 0.6)`` into the Vsa term leaves every computed
    number identical, so only a structural check sees it.

    The module's real ternaries (``1.25 if condition == A else 1.4``,
    ``1.0 if hef < 65.0 else 2.0``) have distinct branches and pass.
    """
    path = pathlib.Path(aci318_anchorage.__file__)
    offenders = _identical_branch_conditionals(path.read_text(encoding="utf-8"))
    assert offenders == [], (
        "fake distinction(s) in "
        f"{path}: " + "; ".join(f"line {ln}: {src}" for ln, src in offenders)
    )


# ---------------------------------------------------------------------------
# 3. The declared scope must survive — including through the public alias
# ---------------------------------------------------------------------------

def test_shear_capacity_docstring_declares_every_known_scope_limit():
    """Keyed on the bold header lines, not on the whole docstring: "futa"
    and "stud" both occur in the Args list and the sourcing note, so a
    substring check let block deletions through. Rewording a header is
    fine; deleting the block that owns a concept is not."""
    doc = inspect.getdoc(shear_capacity) or ""
    headers = _bold_headers(doc)
    for concept, why in [
        ("stud", "case (a), welded headed studs, coefficient 1.0"),
        ("sleeve", "case (c), sleeves through the shear plane, ACI 355.2"),
        ("grout", "the built-up grout pad 0.80 multiplier"),
        ("futa", "the futa cap this function does not enforce"),
        ("phi", "the unresolved phi for steel in shear"),
    ]:
        assert any(concept in h.lower() for h in headers), (
            f"no declaration block owns {why!r} any more (no bold header "
            f"mentions {concept!r}). Headers found:\n" + "\n".join(headers)
        )
    assert len(headers) >= 5, (
        "shear_capacity docstring lost one of its bold scope blocks; "
        f"found {len(headers)}: {headers}"
    )


def test_shear_capacity_docstring_keeps_its_citations_labelled_unverified():
    """The case split, the 1.0 stud coefficient and the 0.80 grout factor
    were reconstructed from secondary sources, not read from the printed
    ACI 318-19. Presenting them as verified citations would be the same
    class of defect this work exists to remove: an assertion the author
    cannot back. The provenance label is part of the deliverable.
    """
    doc = inspect.getdoc(shear_capacity) or ""
    low = doc.lower()
    assert any(h.startswith("**Sourcing") for h in _bold_headers(doc)), (
        "shear_capacity docstring lost its dedicated '**Sourcing' block; "
        "without it the (a)/(b)/(c) case split and the 1.0 stud coefficient "
        f"read as verified citations:\n{doc}"
    )
    assert "secondary source" in low, (
        "shear_capacity docstring dropped its sourcing note; the (a)/(b)/(c) "
        f"split and the 1.0 / 0.80 values are not verified:\n{doc}"
    )
    assert "not verified" in low, (
        "shear_capacity docstring no longer flags the unverified ACI 318-19 "
        f"clause numbering:\n{doc}"
    )


def test_welded_studs_are_declared_in_scope_of_the_module_but_not_of_the_formula():
    """This module advertises "cast-in headed anchors", which *includes*
    welded headed studs, so case (a) is a gap inside its own declared
    scope — not something excused by the module's framing. The docstring
    has to say so in its own dedicated block, with the coefficient a stud
    would take, rather than leaning on the module header.
    """
    mod_doc = (inspect.getdoc(aci318_anchorage) or "").lower()
    assert "cast-in headed" in mod_doc
    doc = inspect.getdoc(shear_capacity) or ""
    stud_blocks = [h for h in _bold_headers(doc) if "stud" in h.lower()]
    assert stud_blocks, (
        "the welded-stud gap must own a bold block in shear_capacity's "
        f"docstring:\n{doc}"
    )
    assert "1.0" in doc, (
        "the welded-stud gap no longer states the coefficient case (a) "
        f"would take:\n{doc}"
    )


def test_public_re_export_carries_the_same_declared_scope():
    """``foundationdesignjm.codes`` re-exports this as ``aci_anchor_shear``,
    and that alias is what ``__all__`` advertises. A wrapper introduced
    later would silently strip the declared limitations from the name
    callers actually import.
    """
    assert aci_anchor_shear is shear_capacity, (
        "aci_anchor_shear is no longer the same object as shear_capacity; if "
        "it is now a wrapper it must carry the scope declarations forward"
    )
    assert "grout" in (inspect.getdoc(aci_anchor_shear) or "").lower()


def test_steel_shear_comment_names_the_case_it_implements():
    """A reader of the formula sees the comment before the docstring. It
    used to say only ``# Steel (17.7.1.2)`` — true, but silent about
    §17.7.1.2 being a *list* of cases of which only one is implemented.
    """
    body = inspect.getsource(shear_capacity).split('"""')[-1]
    assert "case (b)" in body, (
        "the steel-shear comment no longer names the single §17.7.1.2 case "
        "implemented:\n" + body
    )
