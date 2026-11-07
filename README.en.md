# foundationcalc

[Español](README.md) · **English**

Foundation design in Python: EN 1997-1, EN 1992-1-1, ACI 318, footings, walls, piles and slabs.

[![CI](https://github.com/jmurgass99/foundationcalc/actions/workflows/ci.yml/badge.svg)](https://github.com/jmurgass99/foundationcalc/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## What it does

- Bearing capacity per EN 1997-1 Annex D (DA1, DA2 and DA3, drained and undrained) and contact pressures with uplift.
- Elastic settlement (Steinbrenner) and Terzaghi 1D consolidation; CPT and SPT correlations.
- Footing flexure and biaxial punching shear per Eurocode 2 and ACI 318-19.
- Combined and strap footings, tower crane footings, cantilever, basement and gravity walls, and piles.
- Seismic check of footings (EN 1998-5) and theory notes in [`docs/theory/`](docs/theory) (in Spanish).

## Install

```bash
pip install git+https://github.com/jmurgass99/foundationcalc.git
```

Optional extras: `numeric` (numpy, scipy, pandas) and `plot` (matplotlib, plotly).

## Example

Seismic check of a 4 × 4 × 0.8 m footing at 1.2 m depth on sand (φ = 34°), with N = 990 kN, H = 100 kN and M = 200 kN·m:

```python
from foundationcalc import Column, Concrete, RectangularFoundation, SoilLayer, SoilType
from foundationcalc.analysis.seismic_footing import SeismicAction, seismic_footing_check

B, t, D = 4.0, 0.8, 1.2
footing = RectangularFoundation(length=B * 1000, width=B * 1000, thickness=t * 1000, embedment_depth=D * 1000)
column = Column(length=500, width=500, pos_x=B * 500, pos_y=B * 500)
sand = SoilLayer(name="sand", thickness=10, soil_type=SoilType.COHESIONLESS,
                 friction_angle=34.0, unit_weight=19.0)

r = seismic_footing_check(footing, column, 990.0, 100.0, 200.0, sand, Concrete(fck=30),
                          SeismicAction(a_g=0.20, S=1.15))
print(round(r.bearing_utilization, 2), round(r.sliding_utilization, 2), round(r.overturning_utilization, 2))
# 0.73 0.25 0.12
```

More cases in [`examples/`](examples).

## What it does not do

- Global slope stability by slices: use [slipcircle](https://github.com/jmurgass99/slipcircle).
- Advanced 3D elastoplastic geotechnical models with discontinuities or transient water flow (PLAXIS, FLAC).
- Piles in rock with complex fracturing or dynamic hydraulic scour without specific studies.
- Soil-structure interaction with non-linear cyclic degradation without experimental calibration.

Details are in [docs/LIMITACIONES.md](docs/LIMITACIONES.md) (in Spanish).

## Tests

```bash
pip install -e ".[test]"
pytest -q
```

## License

MIT. See [LICENSE](LICENSE). Author: [Jesús Murgas](https://github.com/jmurgass99).
