# 06 — Retaining Walls

> Synthesised from: *UPC – Retaining Walls + Basement Wall PDFs + EC7 examples PDF*.

## 6.1 Wall typologies
- **Gravity wall** (mass concrete, gabion).
- **Cantilever wall** (T or L stem on a base with toe and heel; variants: only heel or only toe, inclined foundation plane, with shear key, counterfort/buttress, with shelves/plates, tieback wall).
- **Reinforced soil walls** with geogrids (Tensar) or galvanised steel strips (Reinforced Earth).
- **Basement walls** — tied at base with floor slab (or grade slab) and at higher floors with slabs. Untied bases NOT allowed in seismic zones.
- **Diaphragm (slurry) walls** and **pile walls** (tangent piles, independent piles).

## 6.2 Lateral earth pressure states

### Movement vs lateral pressure
- ΔH/H ≈ +0.001 to +0.04 (loose sand → soft clay) — **active** pressure mobilised by wall moving away from soil.
- ΔH/H ≈ −0.01 to −0.05 — **passive** pressure mobilised when wall pushes into soil.

### At-rest (no movement)
```
σ'_o   = q + γ·z
σ'_h   = K_o · σ'_o
σ_h    = σ'_h + u                u = γ_w · (z − d_w)
K_o    = (1 − sin φ') · OCR^(sin φ')        (OCR ≥ 1)
```

### Rankine (frictionless wall, smooth back face)
```
K_a = tan²(45° − φ'/2)             K_p = tan²(45° + φ'/2)
σ'_a = σ'_o · K_a − 2·c'·√K_a       σ'_p = σ'_o · K_p + 2·c'·√K_p
P_a = (1/2)·K_a·γ·H²               P_p = (1/2)·K_p·γ·H²
z_c (tension crack)  = 2·c' / (γ·√K_a)
```
Slip-plane angles: ±(45 + φ/2) for active, ±(45 − φ/2) for passive.

### Coulomb (wall friction δ' considered)
```
K_a = sin²(β + φ') / { sin²β · sin(β − δ') · [1 + √( sin(φ'+δ')·sin(φ'−α) / (sin(β−δ')·sin(α+β)) )]² }
K_p = sin²(β − φ') / { sin²β · sin(β + δ') · [1 − √( sin(φ'+δ')·sin(φ'+α) / (sin(β+δ')·sin(β+α)) )]² }
```
- β = inclination of wall back face from horizontal.
- α = backfill slope from horizontal.
- δ' = wall-soil friction angle.

### Wall friction & adhesion
- δ_d = k · φ_cv,d where k = 2/3 (precast) or 1.0 (cast-in-place).
- Passive resistance: γ_R,e = 1.4 in DA-2; γ_G,fav = 1.0 in all DAs.

## 6.3 Cantilever wall — analysis

**Heel wide enough for Rankine**: `b ≥ h · tan(45° − φ/2)`. Then a Rankine zone forms within the soil over the heel and the virtual back-of-wall plane is vertical. P'_a is inclined at angle β to horizontal (parallel to ground surface).

If heel narrow, treat the backfill inside the inclined virtual plane as part of the wall:
```
P'_ah = P'_a · cos(θ + δ)
P'_av = P'_a · sin(θ + δ)
θ      = arctan(b / h)
```

### Mass gravity wall (Coulomb)
```
σ'_ah = K_aγ · (∫γdz − u) + K_aq · q − K_ac · c'
K_aγ  = K_n · cos β · cos(β − θ)
K_aq  = K_n · cos²β
K_ac  = (K_n − 1) · cot φ
```

## 6.4 ULS verifications for a cantilever wall

- **Toppling** (overturning) about toe.
- **Sliding** at base.
- **Bearing** capacity of foundation.
- **Overall stability** (slip surface engulfing the wall).
- **Structural failure** of stem, base.

Eccentricity for bearing: `e_B = B/2 − (M_Ed,stb − M_Ed,dst) / V_d`. Must verify e_B ≤ B/6 for middle-third.
Effective area: A' = B' × L' (per §4.1).

## 6.5 Worked example — Cantilever wall on clay (already in `04_eurocode7_examples.md`)

Summary of governing utilization:
| Check | DA1-C1 | DA1-C2 | DA-2 | DA-3 |
|---|---:|---:|---:|---:|
| Sliding | 43% | **59%** | 47% | 59% |
| Bearing | 47% | **59%** | 65% | 64% |
| Toppling | 30% | 30% | 30% | 30% |

## 6.6 Unplanned excavation
EC7 requires accounting for `ΔH = min(10%·H, 0.5 m)` increase in retained height during design.

---

## Implementation notes

| Concept | Module |
|---|---|
| `K_0`, `K_a`, `K_p` (Rankine) | `analysis.earth_pressure.rankine_*` |
| `K_a`, `K_p` (Coulomb) | `analysis.earth_pressure.coulomb_*` |
| Tension crack depth | `analysis.earth_pressure.tension_crack_depth` |
| Total active/passive thrust + moment | `analysis.earth_pressure.thrust_force` |
| Wall friction angle | `core.materials.WallFrictionCoefficient` |
| Heel check (Rankine vs Coulomb) | `analysis.retaining_walls.virtual_plane_check` |
| Toppling check | `analysis.retaining_walls.overturning_check` |
| Sliding check | `analysis.retaining_walls.sliding_check` |
| Bearing check (use bearing_capacity) | `analysis.retaining_walls.bearing_check` |
| Unplanned excavation | `analysis.retaining_walls.unplanned_excavation` |
