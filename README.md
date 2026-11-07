# foundationcalc

**Español** · [English](README.en.md)

Diseño de cimentaciones en Python: EN 1997-1, EN 1992-1-1, ACI 318, zapatas, muros, pilotes y losas.

[![CI](https://github.com/jmurgass99/foundationcalc/actions/workflows/ci.yml/badge.svg)](https://github.com/jmurgass99/foundationcalc/actions/workflows/ci.yml)
[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-green)](LICENSE)

## Qué hace

- Capacidad portante según EN 1997-1 Anexo D (enfoques DA1, DA2 y DA3, drenada y no drenada) y presiones de contacto con despegue.
- Asientos elásticos (Steinbrenner) y consolidación 1D de Terzaghi; correlaciones CPT y SPT.
- Flexión de zapatas y punzonamiento biaxial según Eurocódigo 2 y ACI 318-19.
- Zapatas combinadas y centradoras, zapatas para grúas torre, muros en ménsula, de sótano y de gravedad, y pilotes.
- Comprobación sísmica de zapatas (EN 1998-5) y teoría en [`docs/theory/`](docs/theory).

## Instalación

```bash
pip install git+https://github.com/jmurgass99/foundationcalc.git
```

Extras opcionales: `numeric` (numpy, scipy, pandas) y `plot` (matplotlib, plotly).

## Ejemplo

Comprobación sísmica de una zapata de 4 × 4 × 0,8 m a 1,2 m de profundidad sobre arena (φ = 34°), con N = 990 kN, H = 100 kN y M = 200 kN·m:

```python
from foundationcalc import Column, Concrete, RectangularFoundation, SoilLayer, SoilType
from foundationcalc.analysis.seismic_footing import SeismicAction, seismic_footing_check

B, t, D = 4.0, 0.8, 1.2
zapata = RectangularFoundation(length=B * 1000, width=B * 1000, thickness=t * 1000, embedment_depth=D * 1000)
pilar = Column(length=500, width=500, pos_x=B * 500, pos_y=B * 500)
arena = SoilLayer(name="arena", thickness=10, soil_type=SoilType.COHESIONLESS,
                  friction_angle=34.0, unit_weight=19.0)

r = seismic_footing_check(zapata, pilar, 990.0, 100.0, 200.0, arena, Concrete(fck=30),
                          SeismicAction(a_g=0.20, S=1.15))
print(round(r.bearing_utilization, 2), round(r.sliding_utilization, 2), round(r.overturning_utilization, 2))
# 0.73 0.25 0.12
```

Más casos en [`examples/`](examples).

## Qué no hace

- Estabilidad global de taludes por dovelas: usa [slipcircle](https://github.com/jmurgass99/slipcircle).
- Modelos geotécnicos tridimensionales elastoplásticos con discontinuidades o flujo transitorio de agua (PLAXIS, FLAC).
- Pilotes en roca con fracturación compleja o socavación hidráulica dinámica sin estudios específicos.
- Interacción suelo-estructura con degradación cíclica no lineal sin calibración experimental.

El detalle está en [docs/LIMITACIONES.md](docs/LIMITACIONES.md).

## Pruebas

```bash
pip install -e ".[test]"
pytest -q
```

## Licencia

MIT. Ver [LICENSE](LICENSE). Autor: [Jesús Murgas](https://github.com/jmurgass99).
