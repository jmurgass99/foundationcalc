# 05 — Deep Foundations (Piles)

> Extracted from: *UPC – Foundation Structures — "Deep Foundations" (1.15)*.

## 5.1 Types

### Main resisting schemes
- **Shaft-friction pile**: capacity from shaft friction along the pile length, in soils whose resistance increases with depth.
- **End-bearing pile**: pile passes through soft soil and rests on a stiff bearing layer.

### Diameter classification
| Type | Diameter |
|---|---|
| Micropiles | 0.08 m < Ø < 0.25 m |
| Medium diameter | 0.25 m < Ø < 0.80 m |
| Large diameter | Ø > 0.80 m |

### Material
- Shaft: steel (profiles, empty or filled tubes), concrete (precast / in-situ), composite (steel + concrete).

### Classification by construction procedure
- **Driven (displacement) piles** — soil is displaced radially. Compression of soil typically improves it.
- **Bored (non-placement) piles** — ground is excavated first. Lateral stresses are reduced during excavation and only partially restored upon concreting.

### Concrete piles
- **Precast** — transported from factory; embedded by percussion, vibration, hydraulic jacks or placed in excavation.
- **In-situ** — formed in a prior excavation, with three subfamilies:
  - **Driven cast in situ** (pyramidal/conical tip, Franki method, by rotation).
  - **Bored** (recoverable casing, lost casing, or with thixotropic mud).
  - **Auger-drilled / CFA** — no casing, concreting via central tube during drilling.

> **Franki piling system**: pressure-injected method to create an expanded base of cast-in-situ concrete.

## 5.2 Structural organisation: pile cap and strap beams

- The **pile cap** distributes the column load among the piles and ties them laterally.
- **Strap beams** stabilise the pile caps laterally and prevent them from separating; they are essential when the cap has 1 or 2 piles (lateral instability otherwise).
- For wall foundations on piles, piles should NOT be in a single vertical plane (lateral instability).

## 5.3 Force distribution in a rigid pile cap

For vertical piles only (rigid cap assumption):
```
F_iv = F_v/n + M_x · y_i / Σy_i² + M_y · x_i / Σx_i²
```
with reference point at the pile-group centroid.

For piles with vertical + horizontal force and possibly different cross-sections (rigid cap):
```
N_i  = (A_i / ΣA_i)·V ± (A_i·y_i / Σ A_i·y_i²)·M_x ± (A_i·x_i / Σ A_i·x_i²)·M_y
H_xi = (A_i / ΣA_i)·H_x ± (A_i²·y_i / Σ A_i²·(x_i² + y_i²))·M_z
H_yi = (A_i / ΣA_i)·H_y ± (A_i²·x_i / Σ A_i²·(x_i² + y_i²))·M_z
```

## 5.4 Individual pile — structural model

### Short piles (< 10 m)
- **Model 1** — fixed at base (end-bearing, bored, in gravel / dense sand, with min embedment in resistant soil).
- **Model 2** — pinned at base (floating piles, no minimum embedment in resistant soil).
- Top of pile considered **fixed** (rotation prevented) if pile-cap-to-pile connection is rigid.
- **Minimum embedment**: 6·Ø in cohesive terrain, 8·Ø in cohesionless.
- **Buckling** must always be considered (especially end-bearing).

### Long piles
- Lateral confinement of the soil must be accounted for. Possibilities:
  - **(A) Winkler model** — soil as lateral springs:
    ```
    F = K·u
    K = s·Ø·w        s = spring spacing, w = ballast coefficient [N/m³]
    ```
  - **(B) Reduced bending length** (clay, constant E with depth):
    ```
    L' = 1.2 · ⁴√(E_p·I_p / (E/3))
    ```

### Criteria for horizontal force H vs vertical V
- H < 0.05·V — horizontal forces may be neglected.
- 0.05·V ≤ H ≤ 0.10·V — piles resist H in bending.
- H > 0.10·V — inclined piles, anchors or passive pressure systems required.

### Group of piles
Model as an **equivalent frame** with length L or L' (reduced bending length).

## 5.5 Pile structural capacity (EHE 58.9)

```
N_d ≤ A_c · f_cd     with f_cd ≤ f_cd,piles (depends on construction type)
```
The PDF lists EHE-58.9 limits for tip-driven piles, bored piles, etc.

## 5.6 Pile-cap structural design (strut-and-tie)

### Cap on 2 piles (rectangular, rigid)

Main bottom tie (per strut-and-tie model for a centred axial Nd; v = half pile spacing, a = column width):
```
T_d = N_d · (v − 0.25·a) / (0.85·d)
```

When the column also applies a moment, superpose two STM solutions and take N_d = max pile force:
```
T_1d = N_d · (v + 0.25·a) / (0.85·d) = A_s · f_yd
```
Secondary reinforcement (transverse): ≥ T_1d / 10. Minimum ≥ 4 ‰ in each direction.

**STM constraint**: f_yd ≤ 400 N/mm².

### Cap on 3 piles (equilateral triangle, side l, column width a)
```
T_d = 0.68 · (N_d / d) · (0.58·l − 0.25·a) = A_s · f_yd
```
Reinforcement placed in strips connecting pile axes (triangular pattern, 60°).

### Cap on 4 piles (rigid)
For different pile forces, take N_d as the maximum. Main bottom reinforcement in bands over the piles (two perpendicular directions):
```
T_1d = (N_d / (0.85·d)) · (0.50·l_1 − 0.25·a_1)
T_2d = (N_d / (0.85·d)) · (0.50·l_2 − 0.25·a_2)
```
Where l_i is the pile spacing in direction i and a_i is the column dimension in the same direction.

Secondary reinforcement: in each direction ≥ ¼ of the main reinforcement.

### General — multiple piles
- Secondary vertical reinforcement: ≥ N_d / (1.5·n), with n = number of piles ≥ 3. Resists the secondary tensile stresses from diagonal-strut opening; T_2d ≈ 0.3·C_d with θ = 45°.
- Main bottom reinforcement strip width = pile diameter + 2·(distance from pile-cap bottom to bar centroid).

### Strap beams for pile foundations
```
b ≥ l/20          h ≥ l/12
M_1d = ±(M_d + N_d·e)          V_1d = M_1d / l
M_2d = ±(q·l² / 12)            V_2d = q·l / 2
q  ≈ 10 kN/m
A_s = A_s' = M_d / d'
```

### Constructive details (pile caps)
- **h_min** ≥ max(40 cm, Ø_pile).
- Pile embedment in cap **≥ 25 cm**.
- Bar spacing **≤ 30 cm**.
- Bar **Ø ≥ 12 mm**.
- Anchor by welding when the cap is shallow.
- Reinforcement patterns by number of piles: **strips** for moderate loads; **diagonals / star** for heavy loads (3, 4, 5, 6 piles).

## 5.7 Bibliography
- Rodríguez Ortiz, Serra, Oteo. *Curso aplicado de cimentaciones*, COAM 1989.
- T. Davidian. *Pilotes y cimentaciones sobre pilotes*. ETASA 1982.
- J. A. Jiménez Salas. *Geotécnia y cimientos* (3 tomos), Ed. Rueda 1980.
- EN 1992-1-1 (Eurocode 2), EN 1997-2 (Eurocode 7 part 2).
- EHE Art. 58, CTE DB SE-C, Normas Tecnológicas de la Edificación — Cimentaciones - Pilotes.

---

## Notes for `foundationcalc`

| Concept | Module |
|---|---|
| Pile model (diameter, material, depth, type) | `core.piles.Pile` |
| Pile group / pile cap | `core.piles.PileCap` (rigid-cap force distribution) |
| Force per pile (vertical only) | `analysis.pile_cap.distribute_forces_vertical()` |
| Force per pile (full 6-DOF) | `analysis.pile_cap.distribute_forces_general()` |
| Short pile structural model | `analysis.pile_structure.short_pile_model()` |
| Long pile Winkler / reduced length | `analysis.pile_structure.long_pile_model()` |
| Cap on 2 piles — STM | `design.pile_cap.cap_two_piles()` |
| Cap on 3 piles — STM | `design.pile_cap.cap_three_piles()` |
| Cap on 4 piles — STM | `design.pile_cap.cap_four_piles()` |
| Secondary reinforcement | `design.pile_cap.secondary_reinforcement()` |
| Strap beam | `design.strap_beam.strap_for_piles()` |
| Bearing capacity (calculation) | `analysis.pile_capacity` |
