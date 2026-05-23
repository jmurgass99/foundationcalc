# 02 — Geotechnical Design according to Eurocode 7 (EN 1997)

> Extracted from: *UPC – Foundation Structures — "Geotechnical Design according to Eurocode 7"*.

## 2.1 The Eurocode family

| Standard | Title |
|---|---|
| EN 1990 | Basis of structural design |
| EN 1991 | Actions on structures |
| EN 1992 | Concrete structures |
| EN 1993 | Steel structures |
| EN 1994 | Composite structures |
| EN 1995 | Timber structures |
| EN 1996 | Masonry structures |
| **EN 1997** | **Geotechnical design** |
| EN 1998 | Earthquake resistance (seismic geotechnical too) |
| EN 1999 | Aluminium structures |

**EN 1997-1 (2004)**: general rules. **EN 1997-2 (2007)**: ground investigation and testing.

EN 1997 does **not** cover seismic design (→ EN 1998).

EN 1997-1 has 12 sections. Spread foundations = §6; piles = §7; retaining structures = §9; hydraulic failure = §10; overall stability = §11; embankments = §12. Annex A gives the **recommended partial factor values** — but the National Annex may modify them.

## 2.2 General principles

- ULS verification: `E_d ≤ R_d`.
- SLS verification: `E_d ≤ C_d`.
- **Partial factors** are applied to actions, geotechnical parameters and resistances.
- Design situations: **Permanent**, **Transient**, **Accidental**, **Earthquake**.
- Both **short-term (undrained)** and **long-term (drained)** conditions must be checked.

### Geotechnical Categories
- **GC1** — small simple projects, negligible risk (column loads ≤ 250 kN, strip loads ≤ 100 kN, retaining walls ≤ 2 m). Satisfied with experience and qualitative investigation.
- **GC2** — conventional projects with medium difficulty. Requires quantitative geotechnical data per EN 1997-2.
- **GC3** — large or unusual structures, abnormal risks, high seismicity, complex soil-structure interaction, bridges > 40 m span, nuclear plants, retaining walls > 10 m, water-pressure > 5 m, single loads > 10 MN. Requires alternative provisions + observational method.

## 2.3 Limit States (5 ULS in EN 1997-1)

| Code | State | Description |
|------|-------|-------------|
| **EQU** | Equilibrium | Loss of equilibrium of the structure or ground as a rigid body; strengths insignificant. |
| **STR** | Structural | Internal failure or excessive deformation of the structure (footings, piles, walls); structural material strength governs. |
| **GEO** | Geotechnical | Failure or excessive deformation of the ground; soil/rock strength governs. |
| **UPL** | Uplift | Loss of equilibrium due to water-pressure uplift or other vertical actions. |
| **HYD** | Hydraulic | Hydraulic heave, internal erosion, piping. |

`E_dst,d ≤ E_stb,d + T_d` for EQU.

## 2.4 Design by calculation

```
F_d = γ_F · F_rep      (actions)
X_d = X_k / γ_M        (soil parameters)
a_d = a_nom ± Δa       (geometry)
R_d = R(F_d, X_d, a_d) / γ_Rd   (resistance)

E_d = E(γ_F · F_rep, X_k/γ_M, a_d)     (sources of γ_F or γ_E applied here)
E_d = γ_E · E(F_rep, X_k/γ_M, a_d)     (alternative, factors applied on effects)
```

### Representative actions
```
F_rep = ψ · F_k
ULS persistent / transient:  Σ γ_G,j G_k,j + γ_P P + γ_Q,1 Q_k,1 + Σ γ_Q,i ψ_0,i Q_k,i
ULS accidental:              Σ G_k,j + P + ψ_1,1 Q_k,1 + Σ ψ_2,i Q_k,i + A_d
ULS earthquake:              Σ G_k,j + P + ψ_2,1 Q_k,1 + A_Ed
```
`ψ_0` = combination, `ψ_1` = frequent, `ψ_2` = quasi-permanent.

## 2.5 Design Approaches (DA-1, DA-2, DA-3)

Partial factor sets:
- **A** — actions (`γ_F`) or effects of actions (`γ_E`). Sets A1, A2.
- **M** — soil parameters (`γ_M`). Sets M1, M2.
- **R** — resistances (`γ_R`). Sets R1, R2, R3, R4.

Combination notation: `A_i "+" M_j "+" R_k`.

| DA | Combination | Actions | Soil | Resistance |
|----|-------------|---------|------|-----------|
| **DA-1** Comb 1 | A1 + M1 + R1 | γ_F ≠ 1 | γ_M = 1 | γ_R = 1 |
| **DA-1** Comb 2 (general) | A2 + M2 + R1 | γ_G=1, γ_Q>1 | γ_M ≠ 1 | γ_R = 1 |
| **DA-1** Comb 2 (piles, anchors) | A2 + M1 (or M2) + R4 | γ_G=1, γ_Q>1 | γ_M = 1 | γ_R > 1 |
| **DA-2** | A1 + M1 + R2 | γ_F ≠ 1 | γ_M = 1 | γ_R ≠ 1 |
| **DA-3** | (A1*/A2†) + M2 + R3 | γ_F ≠ 1 | γ_M ≠ 1 | γ_R = 1 |

* on structural actions; † on geotechnical actions.

### National adoption (informative, Bond 2012)
- **Spain — DA-2** for foundation design; **DA-3** for slope & overall-stability.
- UK: 1/2/3 all admitted.
- Germany, Sweden, Switzerland, Denmark: DA-3.
- France, Italy, Portugal: DA-2.
- Iceland, Belgium, Poland, Hungary, Ireland (default): DA-1.

### DA-2 vs DA-2*
- **DA-2**: `R_d = R(γ_F · F_rep, X_k, a_d) / γ_R`. Partial factors on actions feed into resistance.
- **DA-2\***: `R_d = R(F_rep, X_k, a_d) / γ_R`. Partial factors applied to effects only — equivalent to traditional global-safety-factor approach: `FS = γ_E · γ_R`.

## 2.6 Annex A — Partial factor values (informative)

### Table A.1 — Actions (EQU)
| Action | Symbol | Value |
|---|---|---|
| Permanent unfavourable | γ_G;dst | 1.10 |
| Permanent favourable | γ_G;stb | 0.90 |
| Variable unfavourable | γ_Q;dst | 1.50 |
| Variable favourable | γ_Q;stb | 0 |

### Table A.2 — Soil parameters (EQU)
| Parameter | Symbol | Value |
|---|---|---|
| Angle of shearing resistance¹ | γ_φ' | 1.25 |
| Effective cohesion | γ_c' | 1.25 |
| Undrained shear strength | γ_cu | 1.40 |
| Unconfined compressive strength | γ_qu | 1.40 |
| Weight density | γ_γ | 1.00 |
¹ Applied to tan φ'.

### Table A.3 — Actions or effects (STR/GEO)
| Action | Symbol | A1 | A2 |
|---|---|---:|---:|
| Permanent unfavourable | γ_G | 1.35 | 1.00 |
| Permanent favourable | γ_G | 1.00 | 1.00 |
| Variable unfavourable | γ_Q | 1.50 | 1.30 |
| Variable favourable | γ_Q | 0 | 0 |

### Table A.4 — Soil parameters (STR/GEO)
| Parameter | Symbol | M1 | M2 |
|---|---|---:|---:|
| Angle of shearing resistance | γ_φ' | 1.00 | 1.25 |
| Effective cohesion | γ_c' | 1.00 | 1.25 |
| Undrained shear strength | γ_cu | 1.00 | 1.40 |
| Unconfined compressive strength | γ_qu | 1.00 | 1.40 |
| Weight density | γ_γ | 1.00 | 1.00 |

### Table A.5 — Resistance factors for spread foundations
| Resistance | Symbol | R1 | R2 | R3 |
|---|---|---:|---:|---:|
| Bearing | γ_R;v | 1.0 | 1.4 | 1.0 |
| Sliding | γ_R;h | 1.0 | 1.1 | 1.0 |

### Table A.6 — Driven piles
| Resistance | Symbol | R1 | R2 | R3 | R4 |
|---|---|---:|---:|---:|---:|
| Base | γ_b | 1.0 | 1.1 | 1.0 | 1.3 |
| Shaft (compression) | γ_s | 1.0 | 1.1 | 1.0 | 1.3 |
| Total / combined (compression) | γ_t | 1.0 | 1.1 | 1.0 | 1.3 |
| Shaft in tension | γ_s;t | 1.25 | 1.15 | 1.1 | 1.6 |

### Table A.7 — Bored piles
| Resistance | Symbol | R1 | R2 | R3 | R4 |
|---|---|---:|---:|---:|---:|
| Base | γ_b | 1.25 | 1.1 | 1.0 | 1.6 |
| Shaft (compression) | γ_s | 1.0 | 1.1 | 1.0 | 1.3 |
| Total / combined (compression) | γ_t | 1.15 | 1.1 | 1.0 | 1.5 |
| Shaft in tension | γ_s;t | 1.25 | 1.15 | 1.1 | 1.6 |

### Table A.8 — CFA piles
| Resistance | Symbol | R1 | R2 | R3 | R4 |
|---|---|---:|---:|---:|---:|
| Base | γ_b | 1.1 | 1.1 | 1.0 | 1.45 |
| Shaft (compression) | γ_s | 1.0 | 1.1 | 1.0 | 1.3 |
| Total / combined (compression) | γ_t | 1.1 | 1.1 | 1.0 | 1.4 |
| Shaft in tension | γ_s;t | 1.25 | 1.15 | 1.1 | 1.6 |

### Table A.9 — Correlation factors ξ from static pile load tests (n piles)
| n | 1 | 2 | 3 | 4 | ≥5 |
|---|---|---|---|---|---|
| ξ₁ | 1.40 | 1.30 | 1.20 | 1.10 | 1.00 |
| ξ₂ | 1.40 | 1.20 | 1.05 | 1.00 | 1.00 |

### Table A.10 — Correlation factors ξ from ground tests (n profiles)
| n | 1 | 2 | 3 | 4 | 5 | 7 | 10 |
|---|---|---|---|---|---|---|---|
| ξ₃ | 1.40 | 1.35 | 1.33 | 1.31 | 1.29 | 1.27 | 1.25 |
| ξ₄ | 1.40 | 1.27 | 1.23 | 1.20 | 1.15 | 1.12 | 1.08 |

### Table A.11 — Correlation factors ξ from dynamic impact tests
| n | ≥2 | ≥5 | ≥10 | ≥15 | ≥20 |
|---|---|---|---|---|---|
| ξ₅ | 1.60 | 1.50 | 1.45 | 1.42 | 1.40 |
| ξ₆ | 1.50 | 1.35 | 1.30 | 1.25 | 1.25 |
Model factors: ×0.85 with signal matching; ×1.10 with pile-driving formula using quasi-elastic head displacement; ×1.20 without that measurement.

### Table A.12 — Pre-stressed anchorages
| Resistance | Symbol | R1 | R2 | R3 | R4 |
|---|---|---:|---:|---:|---:|
| Temporary | γ_a;t | 1.1 | 1.1 | 1.0 | 1.1 |
| Permanent | γ_a;p | 1.1 | 1.1 | 1.0 | 1.1 |

### Table A.13 — Retaining structures
| Resistance | Symbol | R1 | R2 | R3 |
|---|---|---:|---:|---:|
| Bearing capacity | γ_R;v | 1.0 | 1.4 | 1.0 |
| Sliding resistance | γ_R;h | 1.0 | 1.1 | 1.0 |
| Earth resistance | γ_R;e | 1.0 | 1.4 | 1.0 |

### Table A.14 — Slopes and overall stability
| Resistance | Symbol | R1 | R2 | R3 |
|---|---|---:|---:|---:|
| Earth resistance | γ_R;e | 1.0 | 1.1 | 1.0 |

## 2.7 Spain — National annexes (UNE-EN 1990 and UNE-EN 1997-1)

### UNE-EN 1990, table AN/8 (EQU, set A)
Permanent — γ_G,inf = 0.90 (stab), γ_G,sup = 1.10 (destab) — both for self-weight and dead loads (with a transient relaxation possible to 0.95 / 1.05).
Earth pressure: stab = 1, destab = 1.35.
Hydrostatic pore-water pressure: stab = 1, destab = 1.35.
Pre-stress: as per applicable Eurocode (auto-equilibrated → ≈ 1).
Variable γ_Q for road/footbridge live load: 0 stab, 1.35 destab; railway 1.45; backfill of walls/abutments 1.50; construction surcharges 1.25; climatic 1.50; water free surface 1.35; hydrodynamic 1.50.

### UNE-EN 1990, table AN/9 (STR/GEO, set B)
Permanent unfavourable γ_G,sup = 1.35; favourable γ_G,inf = 1.00.
Imposed deformations / settlements: 1.20 (linear), 1.35 (non-linear evaluation).
Pre-stress in anchoring zones: 1/1.20 (or 1.30).
Imposed deformations: γ_Q ψ.
Variable γ_Q: 1.35 typical, 1.45 railway bridges, 1.50 wall/abutment fill and climatic, 1.35 hydrostatic free water, 1.50 hydrodynamic.

### UNE-EN 1997-1, table A.2 (EQU) — soil parameters
Same as EU Annex A.2: γ_φ' = γ_c' = 1.25, γ_cu = γ_qu = 1.40, γ_γ = 1.00.

### UNE-EN 1997-1, table A.3.b (STR/GEO global stability, set A2)
Permanent γ_G = 1.0 (both favourable and unfavourable in this Spanish set — note: applied to actions acting on the soil, e.g. structural or traffic loads), variable unfavourable γ_Q = 1.3, favourable = 0.

### UNE-EN 1997-1, table A.4.b (γ_M for global stability, set M2)
γ_c, γ_tanφ, γ_cu values vary by limit state and design situation:
| Limit state / actuation | Persistent | Transient | Accidental |
|---|---|---|---|
| Global stability without structure on crown | 1.40 | 1.25 | 1.15 |
| Structures in roadworks | 1.50 | 1.50 | 1.15 |
| Structures in maritime / port works | 1.40 | 1.40 | 1.15 |
| Structures in buildings | 1.80 | 1.80 | 1.30 |
γ_γ = 1.0 in all cases.

### UNE-EN 1997-1, table A.5 (γ_R for spread foundations, set R2)
| Action | Symbol | Buildings | Other structures |
|---|---|---:|---:|
| Bearing / hundimiento | γ_R;v | 2.15 | 1.85 |
| Sliding | γ_R;h | 1.10 | 1.10 |

> **Note for the Spanish profile**: bearing γ_R;v = 2.15 (buildings) is significantly higher than the EU default R2 = 1.4 — this is the dominant Spanish practice for foundation design and must be selectable in the API.

## 2.8 SLS

`E_d ≤ C_d` with γ = 1.0. EN 1997-1 Annex H: sagging mode, max relative rotations 1/2000–1/300 (typical 1/500 acceptable, 1/150 ≈ ULS). Halved for hogging. Normal isolated foundations: **total settlement up to 50 mm** often acceptable.

### Definitions of foundation movements
- s — settlement.
- δs — differential settlement.
- θ — rotation.
- α — angular strain.
- Δ — relative deflection.
- Δ/L — deflection ratio.
- ω — tilt.
- β — relative rotation / angular distortion.

---

## Notes for `foundationdesignjm`

The API must expose:
1. **Design Approach** selector (DA1-C1, DA1-C2, DA2, DA2*, DA3).
2. **Country / National Annex** profile selector: e.g. `EU_RECOMMENDED`, `SPAIN`, `UK`, `GERMANY`, with their own values for `γ_R;v`, etc.
3. **Limit state** classification: `EQU`, `STR`, `GEO`, `UPL`, `HYD`, `SLS`.
4. **Partial factor sets** A1/A2/M1/M2/R1/R2/R3/R4 as data tables.
5. **Combination factors** ψ_0, ψ_1, ψ_2 per action category.
6. **Correlation factors** ξ₁…ξ₆ for pile load testing.
