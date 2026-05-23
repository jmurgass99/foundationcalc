# 03 — Shallow Foundations (Structural Design)

> Extracted from: *UPC – Foundation Structures — "Shallow Foundations" Part 1 + Part 2 (Luca Pelà)*.

## 3.1 Soil-Structure Interaction (SSI)

The contact pressure distribution under a footing depends on:
- **Rigidity** of the footing (flexible vs rigid).
- **Soil nature** (cohesive vs non-cohesive).

| Footing | Cohesive soil | Non-cohesive soil |
|---|---|---|
| **Rigid** (h ≥ v/2) | Saddle-shaped, max at edges, dips at centre | Parabolic, max at centre, ≈ 0 at edges |
| **Flexible** (h < v/2) | Wider but smoother, max near centre | Bell-shaped, concentrated near load |

For **distributed load**:
- Cohesive: stress bulb is wider laterally.
- Non-cohesive: stress bulb is more focused under the load.

`v` = cantilever (column edge to footing edge).

### Practical pressure model assumptions
For design under the EC7 framework we assume:
- The footing is **rigid** unless explicitly noted.
- The contact pressure varies **linearly** under axial + biaxial moment (Navier).

## 3.2 Eccentricity & contact pressure (1D)

For width `a`, eccentricity `e = M/N`:

| Case | Condition | σ_max |
|------|-----------|-------|
| a | e = 0 | σ_m = N / (a·b) |
| b | e < a/6 | N/(a·b) + 6Ne/(b·a²) |
| c | e = a/6 | 2N/(a·b) |
| d | e > a/6 | 2N/(a'·b) with a' = 3·(a/2 − e) (active zone) |

When e > a/6, part of the footing lifts off. Active length `a' = 3·(a/2 − e)`.

## 3.3 Biaxial bending — Navier

`σ = N/A ± (Mx / Ix)·y ± (My / Iy)·x`

For a rectangle (a × b) with eccentricities e_x = M_y/N, e_y = M_x/N (sign per direction):

```
σ_corner = N/(a·b) ± 6·e_x·N/(a²·b) ± 6·e_y·N/(a·b²)
```

**Middle-third (core of inertia) check** — to keep the entire base in compression:

```
6·|e_x| / a + 6·|e_y| / b ≤ 1
```

If exceeded, an inactive (uplift) zone develops at one corner — the closed-form solution is more involved (use iterative solver for the active polygon).

## 3.4 Rigid vs flexible footing — design model

`v` = cantilever length from column edge to footing edge.

- **Flexible**: v ≥ 2·h → general beam theory (one-way / two-way bending, EC2 reinforcement).
- **Rigid**: v < 2·h → strut-and-tie model.

### 3.4.1 Flexible footing (beam-theory design)

Reference section for bending: offset **0.15·a inside the column** (or **0.25·a** for a masonry wall).

#### Reinforcement distribution
- **Long side a'**: reinforcement uniformly across width b'.
- **Short side b'** (if footing is rectangular, b' ≤ a + 2h is the central strip): a fraction `2·b'/(a' + b')` of A_s in the central strip; the rest distributed in the lateral strips.

#### Shear (one-way)
Check at **distance d from column face** in both directions. Calculate as a beam **without transverse reinforcement** per EC2:

```
V_Rd,c per EC2 §6.2.2
```

#### Punching (two-way)
Critical perimeter at **2d** from column face:
```
u_1 = 2·c_1 + 2·c_2 + 4·π·d
```

Effective punching shear:
```
τ_sd = F_sd,ef / (u_1 · d)
F_sd,ef = β · F_sd
F_sd     = N_sd · (A_footing − A_u1) / A_footing      (uplift inside u_1 deducted)
A_u1     = c_1·c_2 + π·(2d)² + 4·d·c_1 + 4·d·c_2
```
Eccentricity correction factor β:
- Interior column: β = 1.15
- Edge column: β = 1.40
- Corner column: β = 1.50

Punching resistance (EC2):
```
τ_Rd = (0.18/γ_c) · ξ · (100·ρ_l·f_ck)^(1/3)
ρ_l   = √(ρ_x · ρ_y) ≤ 0.02
ξ     = 1 + √(200/d) ≤ 2.0     (d in mm)
```

Required: `τ_sd ≤ τ_Rd`.

### 3.4.2 Rigid footing (strut-and-tie)

Beam theory not valid. Use **strut-and-tie** with isostatic lines.

Simplified S-T model — design tension tie:
```
T_d = A_s · f_yd = N_1d / (0.85·d) · (x_1 − 0.25·a)
```
Where:
- a = column width.
- x_1 = distance from footing edge (where the compression strut lands) to the column centre/axis.
- 0.85·d is the inner lever arm.
- Equilibrium: R_1d · x'_1 = T_d · 0.85·d, with x'_1 = x_1 − 0.25·a, R_1d = N_1d.
- **Restriction:** f_yd ≤ 400 N/mm² in the strut-and-tie method (EHE / EC2 truss model limit).

## 3.5 Inverted T-beam strip footing — modelling

For a long strip foundation with several column loads, the contact pressure depends on the **relative rigidity** of structure and beam:

| Case | Pattern | Comment |
|---|---|---|
| Rigid superstructure + flexible beam | Uniform q on soil | All columns settle uniformly. |
| Flexible superstructure + rigid beam | q linear (trapezoidal/triangular) | Beam tilts. |
| Otherwise | Use **Winkler model** | Soil = springs k_s. |

Dimensioning aid: with two equal column loads P spaced L, with side cantilevers `v` (0 ≤ v ≤ 0.4·L), uniform contact `q = 2P / (L + 2v)`. At v = 0.4·L the positive central moment M⁺ approximately equals the negative cantilever moment M⁻ — typically the most economical layout.

## 3.6 Mat foundations

For a **rigid mat** on deformable soil, uniform pressure is acceptable. In general, prefer **Winkler springs** for accurate stress distribution.

Mat types: (a) flat plate, (b) thickened under columns, (c) beam-and-slab, (d) plate with pedestals, (e) cellular (basement walls as part of mat), (f) post-tensioned slab.

When to use a mat (already in §1.3): individual footings >½ area, mixed soft/stiff strata, differential settlement governs, hydrostatic uplift, etc.

## 3.7 Strap beams

**Definition** — RC elements connecting two or more footings.

**Functions**:
1. Resist horizontal forces from the structure (earthquake, wind).
2. Avoid differential settlements (compatibility tie).
3. Resolve eccentric footings (boundary-line columns).

**Geometry (Spain)**:
- b_min = 30 cm.
- H ≥ L/12, with H ≥ 35 cm.

**Design forces**:
- Pure tension/compression: T = 0.03·(N_1 + N_2) where N_i are the axial loads from the linked columns.
- Vertical overload distributed > 10 kN/m.

**Use of strap beams in Spain (NCSE-02)**:
- **Perimeter connection**: near excavations or slopes; or footings in medium seismic zones (a_c > 0.08 g). Load to resist `T = (a_c/g)·(N_1 + N_2)`.
- **Full 2D connection**: buildings on slopes, footings in high seismic zones (a_c > 0.16 g), or piles in medium-to-high seismic zones.

### 3.7.1 Eccentric (boundary-line) footing — without strap beam

Issues:
- σ_max may exceed soil's ultimate capacity.
- Possible settlement / overturning of the footing.
The triangular pressure distribution under uplift leaves an active length `3c` where `c` is the distance from the column to the heel.

### 3.7.2 With strap beam (the typical solution)

The strap beam transfers part of the moment from the boundary footing to the interior footing. The system can be modelled as two-rigid-bars with the strap as a force-distributor; design results in:
- Higher shear V₁ at the boundary footing.
- Bending moment M₁ along the strap, sign-changing near each footing.
- Footing 2 (interior) carries additional axial via the strap.

### 3.7.3 Alternative (no strap beam)

The eccentric footing is enlarged and detailed so that the moment from the wall above is resisted by the concrete weight + soil pressure redistribution (see fig. 18 of the deck).

## 3.8 Constructive details

- Minimum depth from ground surface: **≥ 50 cm** (frost / topsoil avoidance).
- **Blinding concrete** ≥ 5 cm under the footing.
- Bar **embedment** ≥ 10 cm (cover).
- Steel bar **spacing ≤ 30 cm**.
- **Min bar Ø ≥ 12 mm** (Spanish practice / EHE).
- Footing minimum thickness:
  - **Reinforced concrete**: ≥ 25 cm.
  - **Plain concrete**: ≥ 35 cm.

## 3.9 Bibliography (Part 1+2)
- J. Calavera, *Proyecto y cálculo de estructuras de hormigón armado para edificios*, INTEMAC 1991.
- J. Calavera & L. García Dutari, *Cálculo de estructuras de cimentación*, INTEMAC 1991.
- J. M. Rodríguez Ortiz, J. M. Serra, C. Oteo, *Curso aplicado de cimentaciones*, COAM 1989.
- J. Calavera, *Muros de contención y muros de sótano*, INTEMAC.
- EHE — Instrucción de Hormigón Estructural, Art. 58°.
- Código Técnico de la Edificación — DB SE-C.

---

## Notes for `foundationdesignjm`

| Concept | Module |
|---|---|
| 1D / 2D Navier pressure with case (e>a/6) | `analysis.base_pressure` (extend) |
| Footing rigidity classification (v vs 2h) | `core.geometry.RectangularFoundation.is_rigid()` |
| Strut-and-tie tie force | `design.strut_and_tie` (new) |
| Flexure design at offset 0.15a / 0.25a | `design.reinforcement.flexure_at_critical_section` |
| One-way shear at d | `design.shear.one_way_shear_check` |
| Punching shear (EC2) | `design.punching_shear.punching_shear_check` |
| Winkler model (mat / inverted T) | `analysis.winkler` (new) |
| Strap-beam design | `design.strap_beam` (new) |
| Boundary-line footing balance | `analysis.eccentric_footing` (new) |
| Detailing limits (cover, bar spacing) | `design.detailing` (new) |
