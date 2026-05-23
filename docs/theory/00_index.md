# Theory Index — FoundationDesignJm

Knowledge base extracted from the *Foundation Structures* course (UPC — Master in Structural and Construction Engineering) and from EN 1990, EN 1992, EN 1997 (Eurocodes), CTE-DB-SE-C (Spain), and EHE.

| # | Document | Modules it informs |
|---|----------|-------------------|
| 01 | [Introduction to foundation structures](01_introduction.md) | `core.geometry`, `core.piles`, `core.soil`, `analysis.bearing_capacity` |
| 02 | [Geotechnical Design according to Eurocode 7](02_eurocode7.md) | `codes.eurocode7` (DA1, DA2, DA3, partial factor sets, national profiles) |
| 03 | [Shallow Foundations (Structural Design)](03_shallow_foundations.md) | `core.geometry`, `analysis.base_pressure`, `design.reinforcement`, `design.punching_shear`, `design.strut_and_tie`, `design.strap_beam` |
| 04 | [EC7 Worked Examples](04_eurocode7_examples.md) | Tests / `analysis.bearing_capacity` validation |
| 05 | [Deep Foundations (Piles & Pile Caps)](05_pile_foundations.md) | `core.piles`, `analysis.pile_cap`, `design.pile_cap`, `analysis.pile_capacity` |
| 06 | [Retaining Walls](06_retaining_walls.md) | `analysis.earth_pressure`, `analysis.retaining_walls` |
| 07 | [Seismic Design](07_seismic.md) | `analysis.seismic`, `design.seismic`, `design.tie_beam` |
| 08 | [Strengthening of Existing Foundations](08_strengthening.md) | `design.strengthening`, `design.serviceability` |

## Reference standards
- **EN 1990** — Basis of structural design.
- **EN 1991** — Actions on structures.
- **EN 1992-1-1** — Design of concrete structures (EC2).
- **EN 1997-1 (2004)** — Geotechnical design, general rules.
- **EN 1997-2 (2007)** — Geotechnical design, ground investigation and testing.
- **EN 1998** — Earthquake resistance (EC8).
- **EHE-08** — Instrucción de Hormigón Estructural (Spain).
- **CTE-DB-SE-C** — Código Técnico de la Edificación, DB Seguridad estructural — Cimientos.

## National Annex profiles supported (target)
- `EU_RECOMMENDED` — Eurocode default (Annex A values).
- `SPAIN` — UNE-EN 1990 / UNE-EN 1997-1 (DA-2 for foundations, DA-3 for slopes/global stability; γ_R,v = 2.15 for buildings).
- `UK` — Combinations 1/2/3 admitted (DA-1).
- `GERMANY` — DA-2*.
- `FRANCE`, `ITALY`, `PORTUGAL` — DA-2 (informative).
