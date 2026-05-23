# 07 — Seismic Design of Foundations and Retaining Structures

> Extracted from: *UPC – Foundation Structures — "Seismic Design of Foundations and Retaining Structures" (A. Drougkas)*.

## 7.1 General requirements
1. Loads must transmit to ground **without significant permanent deformations**.
2. Soil deformation induced by the earthquake must be **compatible with the essential functions of the structure**.
3. Care against **liquefaction, geological faults, landslides**.

### Design rules
- Do not combine **different foundation types** in one dynamic unit.
- If soil is not homogeneous, use **independent dynamic units**.
- Foundation must be **sufficiently rigid** to transmit loads uniformly.
- Account for **relative horizontal displacements** of vertical members.
- Reduction of seismic amplitude **with depth** may be considered (limits).
- **Monolithicity** as a key property against differential movements.
- Massive and stiff foundation evenly distributes stresses to the ground.

## 7.2 Liquefaction (cohesionless soils below WT)

### Definition
Reduction of resistance and/or stiffness caused by an **increase of pore water pressure**, leading to permanent deformations or quicksand condition.

### EC8 criteria (when liquefaction check NOT required)
With shallow foundation, there is no liquefaction potential if **saturated sand layer is below 15 m** depth.

If design ground acceleration `α · S < 0.15`, no check is required if any of:
- Clay > 20% with PI > 10.
- Silt > 35% with N_1(60) > 30.
- Clean sand with N_1(60) > 30.

### Normalised SPT
```
N_1(60) = (100 / σ'_v0)^(1/2) · N_SPT
0.5 < (100/σ'_v0)^(1/2) < 2
```

### Cyclic tangential seismic stress
```
τ_e = 0.65 · α · S · σ_v0      (valid for z ≤ 20 m)
```
A magnification coefficient `C_M` adjusts τ_e for surface-wave magnitudes ≠ M_s 7.5:
| M_s | C_M |
|---|---|
| 5.5 | 2.86 |
| 6.0 | 2.20 |
| 6.5 | 1.69 |
| 7.0 | 1.30 |
| 8.0 | 0.67 |

### Countermeasures
- **Soil improvement**: compaction/vibration to raise penetration above critical value; drainage; jet grouting.
- **Pile foundations**: cautious — when soil liquefies, large lateral loads are introduced; uncertainty in layer location/thickness.

## 7.3 Isolated footings (1–2 storey buildings)

- Compression force restricts overturning.
- Form **plastic hinge at base of column** — flexural overstrength required at column-footing joint.
- **Rocking / tipping** can occur if footing is too small — leads to permanent tilt.

### Sliding resistance
```
Above WT:  F_Rd = N_Ed · tan δ / γ_M       δ ≈ 0.50·φ, γ_M = 1.25
Below WT:  F_Rd = c_u · A' / γ_M           (undrained)
V_Ed ≤ F_Rd + E_pd                         (E_pd = passive earth pressure)
```

### Capacity-based design
Foundation remains elastic considering overstrength of plastic hinges:
```
M_d = M_u,col · γ_SR             γ_SR = 1.35 (overstrength factor)
```

## 7.4 Tie / strap elements (foundation-level)

### Required design forces (EC8)
- ±0.3·α·S·N_Ed for ground type B.
- ±0.4·α·S·N_Ed for ground type C.
- ±0.6·α·S·N_Ed for ground type D.

Where N_Ed is the mean axial force from the connected vertical elements (seismic situation).

### Minimum dimensions
- Width ≥ 250 mm.
- Depth ≥ 400 mm (up to 3 storeys above basement); ≥ 500 mm (4+ storeys).

### Minimum reinforcement
- EC8: ρ_min = 0.4% top + bottom.
- EHE (08): ρ_min = 0.28% top + bottom.

### When are tie beams mandatory? (Spain)
- a_c > 0.16·g → tie beams mandatory (both directions for footings/piles).
- a_c < 0.16·g → grade slab with h > 0.15 m and h > L_between_piers/50.

## 7.5 Pile foundations (seismic)

Dissipation mechanisms:
- **Plastic hinge** at base of vertical structural element (good).
- Plastification of pile in tension — cracks below ground (bad).
- Slipping of pile in soil (friction loss).

Lateral force effects on piles: difficult to predict; design solutions:
- Small distance between peak moments (higher shear demand).
- Design for high ductility.
- Improve soil.

### Specific rules (EC8 pile rebar)
- Longitudinal Ø ≥ 12 mm; clear radial spacing d < 200 mm.
- Minimum reinforcement: 0.4% cast in situ; 1.0% precast.
- Stirrups Ø ≥ 6 mm. Critical zone: 0.8% min, max spacing 100 mm. Other parts: 0.6%, max spacing 150 mm.

## 7.6 Mononobe-Okabe (M-O) — seismic earth pressure on walls

### Pseudo-static design earth pressure
```
E_d = (1/2)·γ*·(1 ± k_v)·K·H² + E_ws + E_wd
```
| Symbol | Meaning |
|---|---|
| γ* | Effective soil unit weight (depends on WT) |
| k_h, k_v | Horizontal / vertical seismic coefficients |
| K | Static + dynamic coefficient of lateral pressure (M-O) |
| E_ws | Hydrostatic lateral force (only below WT) |
| E_wd | Hydrodynamic lateral force (only below WT) |

### Mononobe-Okabe K coefficient

If `β ≤ φ'_d − θ`:
```
K = sin²(ψ + φ'_d − θ) / { cos θ · sin²ψ · sin(ψ − θ − δ_d) · [1 + √( sin(φ'_d + δ_d) · sin(φ'_d − β − θ) / (sin(ψ − θ − δ_d) · sin(ψ + β)) )]² }
```

If `β > φ'_d − θ`:
```
K = sin²(ψ + φ'_d − θ) / { cos θ · sin²ψ · sin(ψ − θ − δ_d) }
```

Where:
- φ'_d = arctan(tan φ' / γ_φ')
- δ_d  = arctan(tan δ / γ_φ')
- ψ    = angle between wall front face and horizontal
- β    = ground slope angle
- δ    = soil-wall friction angle
- θ    = seismic inertia angle (see below)

### Soil unit weight and θ (depends on WT and permeability)

| Condition | γ* | tan θ | E_wd |
|---|---|---|---|
| WT below wall base | γ | k_h / (1 ∓ k_v) | 0 |
| WT above, dynamic impermeability | γ_s − γ_w | (γ_s / (γ_s − γ_w)) · k_h/(1∓k_v) | 0 |
| WT above, high dynamic permeability | γ_s − γ_w | (γ_d / (γ_s − γ_w)) · k_h/(1∓k_v) | (7/12)·k_h·γ_w·H'² |

### Rigid walls (cannot generate active state)
Dynamic increment:
```
ΔP_d = α · S · γ · H²
```
Applied at **mid-height** of the wall.

### Tieback walls
The anchorage length increases because seismic effects reduce angle α_AE → larger active pressure / larger passive reaction at bulb. Design method: Ebeling & Morrison (1993).

### Reinforced earth walls (M-O equivalent, FHWA-style)

External stability:
1. Determine peak horizontal ground surface acceleration a_max.
2. Peak acceleration at centroid of reinforced zone:
   ```
   a_c = (1.45 − a_max/g) · a_max
   ```
3. Dynamic soil thrust (γ⁽ᵇ⁾ = backfill unit weight):
   ```
   ΔP_AE = 0.375 · a_c · γ⁽ᵇ⁾ · H² / g
   ```
4. Inertial force on reinforced zone (γ⁽ʳ⁾ = reinforced-zone unit weight):
   ```
   P_IR = a_c · γ⁽ʳ⁾ · H · L / g
   ```
5. Stability for P_A + ΔP_AE + 50%·P_IR.

---

## Implementation notes

| Concept | Module |
|---|---|
| Liquefaction screening (EC8 criteria) | `analysis.seismic.liquefaction_screening` |
| N_1(60), τ_e | `analysis.seismic.normalized_spt`, `cyclic_stress_ratio` |
| Mononobe-Okabe K | `analysis.seismic.mononobe_okabe_K` |
| Pseudo-static design force | `analysis.seismic.seismic_thrust` |
| Rigid-wall ΔP_d | `analysis.seismic.rigid_wall_dynamic_increment` |
| Reinforced-earth external stability | `analysis.seismic.reinforced_earth_external` |
| Foundation tie design force | `design.tie_beam.seismic_tie_force` |
| Capacity design factor | `design.seismic.overstrength_factor` |
