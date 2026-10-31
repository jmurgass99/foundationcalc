# 09 — Basement Walls

> Extracted from: *UPC – Foundation Structures — "Basement Wall"* (Miquel Rodriguez Niedenführ).

## 9.1 What makes a basement wall different from a retaining wall?

A retaining wall is **free to rotate / translate** outwards — so the
**active** state develops and `K = K_A`. A basement wall is **restrained
at the top** (by the ground-floor slab) and often at intermediate floor
slabs and at the base (by the foundation slab + the floor of the
basement). The wall cannot move enough to mobilise the active state, so
the design pressure is the **at-rest** pressure `K = K_0`.

Three boundary-condition cases (from the slides):
1. Bottom support by a floor slab → both ends restrained (propped or
   continuous beam).
2. Bottom support by the pavement / rigid slab → idem.
3. Without rigid bottom slab → the wall foundation must provide the
   shear restraint by friction at the base.

## 9.2 Static models

For the typical single-basement case the wall is modelled as a
**propped cantilever**:
- Pinned at the top (the ground-floor slab acts as a horizontal strut).
- Fixed at the base (the wall-foundation joint is moment-resistant).

For walls restrained by **several intermediate slabs** the wall behaves
as a continuous beam over multiple supports.

The slides show that the design moment is taken as the envelope of two
static schemes: a pinned-pinned beam and a propped cantilever — this
covers the uncertainty on whether the base joint behaves as fully fixed
or pinned.

## 9.3 Lateral pressure distribution

| Approach | Diagram |
|---|---|
| (a) At-rest, triangular (Coulomb / Rankine extrapolation) | σ_h(z) = K_0·(γ·z + q) |
| (b) Rectangular approximation | σ_h = 0.67·K_0·(γ·H + q), uniform |
| (c) Two-restraint case | Two rectangular blocks 0.67·K_0·(γ·H/2 + q) each on the upper and lower halves |

`K_0 = 1 − sin φ'` (Jaky, non-overconsolidated soils).

## 9.4 Load combinations

The slides recommend designing for three combinations:
1. **Construction**: self weight + lateral pressure + N_min (typically
   N_min = 0 during construction before the upper structure is built).
2. **In service**: self weight + lateral pressure + N_max.
3. **No lateral soil**: self weight + N_max (e.g. excavation around the
   basement during the building lifetime).

For each combination the resulting axial force and bending diagrams are
combined and the envelope is used to design the reinforcement.

## 9.5 Closed-form moments and reactions

**Propped cantilever, triangular load `q(z) = q_0 · z/H`** (z from the top):

| Quantity | Value |
|---|---|
| Top reaction T_top | + q_0·H/10 |
| Base reaction T_base | + 2·q_0·H/5 |
| Max sagging M_max (at z = H/√5 ≈ 0.447 H) | + q_0·H² · √5 / 75 ≈ 0.0298 q_0·H² |
| Base hogging moment (fixed end) | − q_0·H² / 15 ≈ 0.0667 q_0·H² |

**Cantilever (free top, fixed at base), triangular load**:
| Quantity | Value |
|---|---|
| Top reaction | 0 |
| Base reaction (= total load) | + q_0·H/2 |
| Base hogging moment | − q_0·H² / 6 |

**Pinned-pinned beam (both ends propped), triangular load**:
| Quantity | Value |
|---|---|
| Top reaction | q_0·H/6 |
| Base reaction | q_0·H/3 |
| Max sagging M (at z = H/√3) | q_0·H²·√3 / 27 ≈ 0.0642 q_0·H² |

For the rectangular pressure diagram `w = const`, the standard formulas
of a beam with uniform load apply (PIC over PP for q·H²/8, propped
cantilever for −q·H²/8 at base and q·H²/(57.4) at the span).

## 9.6 Combined N + M

The axial force from the upper structure creates a second-order moment
in the wall:
```
M_top = e_1 · N_max         (M at the top of the wall due to N eccentricity)
M_base = −e_2 · ΣN_max      (M at the base from the resultant axial)
```
Where `e_1` and `e_2` are the construction eccentricities at top and
base of the wall (e.g. the column above and the wall-foundation
intersection).

The total bending diagram is the **algebraic sum** of:
- Lateral-pressure moment diagram (above).
- Linear diagram from `M_top` to `M_base`.
- Uniform `N(z)` increasing with depth (self weight).

This produces the envelopes M' (towards the soil) and M" (towards the
basement) that govern the reinforcement of the inner and outer face
respectively.

## 9.7 Constructive requirements (CTE / EC2)

- Minimum thickness: 0.20 m (typical 0.25–0.30 m for residential
  basements).
- Inner-face reinforcement: governed by sagging moments.
- Outer-face reinforcement: governed by hogging moments at the base
  joint with the foundation.
- Horizontal reinforcement ratio ≥ 0.10 % of A_c (EC2 §9.6.3 minimum
  for walls).
- Waterproofing membrane on the outer face + drainage channel at the
  base (perforated pipe in gravel).
- Construction joints with water-stop bars.

---

## Notes for `foundationcalc`

| Concept | Module |
|---|---|
| Static schemes (cantilever, propped cantilever, pinned-pinned) | `design.basement_wall.SupportConfig` |
| At-rest triangular vs rectangular pressure | `design.basement_wall.PressureDiagram` |
| Closed-form M and V envelopes | `design.basement_wall.BasementWallDesigner.envelope` |
| 3-combination loading (construction, service, no soil) | `design.basement_wall.LoadingCase` |
