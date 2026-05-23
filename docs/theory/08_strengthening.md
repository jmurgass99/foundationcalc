# 08 — Strengthening of Existing Foundations

> Extracted from: *UPC – Foundation Structures — "Strengthening of Existing Foundations" (1.9)*.

## 8.1 Effects of foundation problems on the structure

### General
- Damage in non-structural elements (partitions, ceilings, pavements).
- Loss of horizontality in floors.

### Masonry buildings
- Wall out-of-plumb.
- Separation between perpendicular walls.
- Distortion and diagonal cracking in walls.
- Differential settlement in walls.
- Deformation/cracking of vaults and arches.
- Cracking/damage in lintels.
- Opening of mortar joints.
- Fragmentation into independent parts.

### RC frame structures
- Extremely sensitive to differential settlement.
- Cracking in columns, beams, slabs.
- Possible shear/bending failure of structural members.

## 8.2 Foundation movement limits

### EC7 Annex H
- SLS: relative rotation 1/2000 to 1/300 (sagging); 1/500 acceptable for many structures.
- ULS: relative rotation ≈ 1/150.
- Hogging values are halved relative to sagging.

### CTE-DB-SE-C (Spain) — limit values
| Type of structure | Angular distortion β limit |
|---|---|
| Isostatic structures and retaining walls | 1/300 |
| Frame with partition walls | 1/500 |
| Precast panels | 1/700 |
| Unreinforced masonry — sagging | 1/1000 |
| Unreinforced masonry — hogging | 1/2000 |

Horizontal distortion ε for load-bearing walls: ≤ 1/2000.

```
β_AB = δs_AB / L_AB = (s_B − s_A) / L_AB
ε_AB = δx_AB / L_AB = (x_B − x_A) / L_AB
```

## 8.3 When to strengthen

Justifications:
- Design/construction defect.
- Active geotechnical problems (long-term deformation, erosion, landsliding, WT variations).
- Material damage or active structural problems (chemical attack, RC deterioration).
- Change of use → meaningful load increase.

### Cautions
- Reliable **contact** between existing foundation and strengthening elements.
- Unfavourable underground execution conditions.
- Difficulty in mechanically activating strengthening (hydraulic jacks).
- Settlements during implementation (water, concrete shrinkage, etc.).
- Possible need to **unload elements** (auxiliary shores).
- Risk of generating anomalous forces.
- Heterogeneous foundations creating new differential settlement.
- Vibrations during drilling.

## 8.4 Strengthening methods for shallow foundations

1. **(Spread or strip) footing replacement** — material or functional elimination of original footing; transfer of capacity to a new element. Hydraulic jacks for functional replacement.
2. **Footing repair** — addition of new material (injection / grouting, mortar repointing, reinforced insertions, replacement of units) or mechanical devices (confinement).
3. **Footing strengthening** — increase section by lateral extension; the new RC envelopes the existing footing.
4. **Deepening of support base** (pit / mass concrete underpinning) — relocate base to deeper, more resistant soil.
5. **Underpinning with deep foundation elements** — convert to deep / hybrid via micropiles or jet-grouting.
6. **Ground improvement** — increase bearing capacity by injections, inclusions, confinement.
7. **Combinations** of the above.

## 8.5 Strengthening of deep foundations

Per the PDF (later sections — high-level summary):
- Addition of **new piles** around existing pile group + new cap envelope.
- **Micropiles** beside existing pile cap.
- **Jet-grouting** to strengthen soil around shaft.

---

## Implementation notes

| Concept | Module |
|---|---|
| Limit angular distortion check | `design.serviceability.angular_distortion_check` |
| Limit horizontal distortion check | `design.serviceability.horizontal_distortion_check` |
| CTE-DB-SE-C and EC7 Annex H limit tables | `codes.serviceability_limits` |
| Strengthening typologies (catalog) | `design.strengthening.StrengtheningType` (enum, mostly informative) |
| Existing footing + extension capacity | `design.strengthening.extended_footing_capacity` |
| Micropile underpinning | `design.strengthening.micropile_underpinning` |
