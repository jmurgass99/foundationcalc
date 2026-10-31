# 01 — Introduction to Foundation Structures

> Extracted from: *UPC – Foundation Structures, Luca Pelà — "Introduction to foundation structures"*.

## 1.1 Definitions

A **foundation** is the part of a structure that supports its weight and transmits the load to the underlying soil or rock. Foundation engineering integrates **geology, soil mechanics, rock mechanics, structural engineering and construction engineering**, and is performed jointly by the **geotechnical engineer** (who provides bearing capacity, soil parameters, presumed bearing pressures) and the **structural engineer** (who performs the structural design proper).

### Geotechnical activities involved
- Selecting **foundation type, depth and dimensions**.
- Calculating **settlement** (total, differential, tilt).
- Determining **bearing capacity** and **design soil bearing pressure**.
- Slope stability investigations.
- Seismic-induced foundation movement and **liquefaction**.
- Durability / deterioration studies.
- **Soil treatment** to increase capacity.
- Retaining-wall foundation parameters.
- Dewatering and **drainage of excavations**.
- Groundwater & seepage analyses.
- Site preparation: compaction specs, density testing.
- **Underpinning** and field testing.

## 1.2 Project requirements

A foundation project must collect:
1. **Topography** of the site (surface, adjacent property, watercourses, trees, access).
2. Location of **buried utilities**.
3. **General geology**, possibility of subsidence.
4. **Previous history and use** of the site (defects, prior failures).
5. **Special hazards** (earthquakes, flooding, swelling/shrinkage, permafrost, erosion).
6. Availability/quality of **local construction materials**.
7. **Hydrographic / meteorological** data for maritime works.
8. Soil/rock strata + **groundwater** within depth of influence.
9. **Lab tests** on soil and rock samples.
10. **Chemical analyses** on soil / groundwater (sulfates, etc.).

These combine with **regulatory** requirements (Eurocodes, national annexes, local codes).

## 1.3 Classification of foundations

### Shallow foundations
- **Spread / pad footing**: square or rectangular, supports a single column.
- **Combined footing**: rectangular or trapezoidal, supports two or more columns.
- **Cantilever / strap footing**: links an eccentric footing (e.g. property-line column) to an interior footing through a strap beam.
- **Strip / wall footing**: long RC element supporting a load-bearing wall.
- **Inverted T-beam**: special strip foundation.
- **Mat / raft foundation**: large continuous slab; subtypes (a) flat plate, (b) plate thickened under columns, (c) beam-and-slab, (d) plate with pedestals, (e) basement walls as part of mat.

When to use a **mat**:
1. Sum of individual footing areas exceeds ~½ the total foundation area.
2. There are **cavities / compressible lenses** — the raft spans them and equalises settlement.
3. Heavy **differential settlements** expected.
4. **Unequal load distribution** on the structure.
5. **Hydrostatic uplift** from high water table.

### Shallow foundation alternatives (when settlements would be too large)
1. **Grading** — remove and replace compressible layer with structural fill.
2. **Surcharge** — preload with fill (use vertical drains to accelerate consolidation).
3. **Densification** of loose-soft soil (vibroflotation, dynamic compaction, compaction grouting).
4. **Floating foundation** — weight of structure balanced by excavated soil.

### Deep foundations
- **Driven piles** (timber, steel, precast concrete).
- **Bored piles / cast-in-place**.
- **Composite piles** (two materials acting together).
- **Precast prestressed RC piles**.

By support behaviour:
- **End-bearing pile**: tip rests on dense/hard stratum → resists by point. Soft layers above can produce **downdrag (negative skin friction)**.
- **Friction pile**: capacity from shaft adhesion/friction (soft clays).
- **Combined**.
- **Batter pile**: inclined, for high lateral loads.

`Q_u = Q_p + Q_s` (point + shaft).

### Typical pile properties (Bowles)
| Pile type | Max length | Optimum length | Max load (typical) |
|-----------|-----------:|---------------:|-------------------:|
| Timber | 35 m | 9–20 m | 270 kN |
| Steel | Unlimited | 12–50 m | f_y · A |
| Cast-in-place w/ shell | 45 m | 9–25 m | 900 kN |
| Cast-in-place no shell | 36 m | 8–12 m | 1 300 kN |
| Concrete-filled steel pipe | Unlimited | 12–36 m | 1 800–18 000 kN |
| Composite | 55 m | 18–36 m | 1 800 kN |
| Precast / prestressed | 30–60 m | 12–18 m | 8 500 kN (PT) / 900 kN (precast) |
| Cast-in-place thin-shell driven | 30 m | 12–18 m | 675 kN |
| Auger-placed (CFA) | 9–25 m | 12–18 m | 700 kN |

## 1.4 Selection of foundation type — drivers

- **Adequate depth** (avoid frost damage, scour in bridge piers).
- Safety against **bearing-capacity failure**.
- **Settlement** must not damage the structure.
- Adequate **durability** (sulfate attack, etc.).
- Adequate **structural strength**.
- Resistance to **adverse long-term soil changes** (expansive soils).
- **Seismic forces**.

## 1.5 Safety factors

Foundations carry **higher safety factors** than the superstructure because:
- Foundations are at the bottom, so extra concrete here does not propagate weight upwards.
- **Construction tolerances** in foundations are wider.
- **Structural materials may be damaged** during installation (piles).
- **Soil properties** are uncertain.
- **Load-transfer mechanism** is uncertain.
- Foundation failures are **costly and catastrophic**.

## 1.6 Bibliography mentioned
- Bowles J. (1998). *Foundations Analysis and Design*. McGraw Hill.
- Day R. W. (2006). *Foundation Engineering Handbook*. McGraw-Hill Professional.

---

## Notes for `foundationcalc`

This section maps to the following modules to be implemented / expanded:

| Concept | Module |
|---|---|
| Pad / spread footing | `core.geometry.RectangularFoundation` (exists, generalise) |
| Combined / trapezoidal footing | `core.geometry.CombinedFoundation` (new) |
| Strap / cantilever | `core.geometry.StrapFoundation` (new) |
| Strip / wall footing | `core.geometry.StripFoundation` (new) |
| Mat / raft | `core.geometry.MatFoundation` (new) |
| Pile / pile group | `core.piles.Pile`, `core.piles.PileGroup` (new) |
| Soil parameters | `core.soil.Soil` (rewrite with φ, c, γ, c_u, E, ν, layered) |
| Bearing-capacity failure | `analysis.bearing_capacity` (new) |
| Sliding failure | `analysis.sliding` (new) |
| Overturning failure | `analysis.overturning` (new) |
| Overall stability | `analysis.overall_stability` (new) |
| Settlement | `analysis.settlement` (new) |
| Negative skin friction | `analysis.piles.downdrag` (new) |
