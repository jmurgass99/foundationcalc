# Changelog

## 1.1.0 — 2026-11-01

### Corregido

- `analysis.stress.boussinesq_strip_load_dsigma_z`: faja flexible integrada analíticamente respecto a la distancia al eje; antes la tensión bajo el eje daba 44,8 kPa (0,448·q) en vez de 55,0 kPa (0,550·q de las tablas de Das para z/b = 2) y en el borde 25,0 en vez de 40,9 kPa. Ahora coincide exactamente con la integral numérica de 20 000 cargas lineales.
- `analysis.consolidation.elastic_settlement_rectangle`: factores de influencia de Steinbrenner I_s en esquina y centro corregidos mediante la formulación canónica; antes, para L/B = 2 daba I = 2,14 (centro real 1,53) y para L/B = 5 daba 7,49 (centro real 2,10), sobreestimando los asientos elásticos más de un 250 %.
- `analysis.winkler.gazetas_stiffness` y `dynamics.foundation_impedance.rectangular_footing_impedance`: unificadas las dimensiones de cálculo a semidimensiones L y B consistentes con NIST GCR 12-917-21 Tabla 2-2a y Gazetas (1991); corregido el factor 2 en la impedancia dinámica que provocaba discrepancias entre ambos módulos.
- `design.punching_shear.punching_shear_check`: añadida la cota inferior de resistencia mínima a cortante v_min según EN 1992-1-1 §6.4.4 Eq. 6.47 para cuantías bajas de armadura longitudinal.
- `analysis.pile_capacity.pile_axial_capacity`: el factor de correlación ξ_3 / ξ_4 toma el cociente gobernante `min(R_m;media / ξ_3, R_m;min / ξ_4) = R / max(ξ_3, ξ_4)` con un único perfil ensayado.
- `analysis.earth_pressure.Ka_rankine_inclined`: corregida la evaluación de Rankine con relleno inclinado; antes para taludes inclinados (p. ej. α = 20°) utilizaba el coeficiente plano de 0,3333 en vez de 0,4142.
- `design.retaining_wall.CantileverWallDesigner`:
  - DA1-C2 evalúa el empuje activo con el ángulo de fricción de cálculo minorado `tan(φ_d) = tan(φ)/1,25` y coeficientes de acción A2 (1,0 G, 1,3 Q).
  - DA1-C1 aplica el coeficiente de seguridad γ_Q = 1,50 al empuje originado por la sobrecarga en cabeza.
  - Comprobación de deslizamiento divide por tan(φ_d) y aplica el factor de resistencia γ_R;e / γ_R;h correspondiente.
  - Momentos flectores en talón y puntera evaluados a partir de las presiones trapezoidales efectivas en la base del cimiento.
  - Estado límite de vuelco EQU evaluado desde valores característicos con 0,90 estabilizante y 1,10 / 1,50 desestabilizante.
- `design.combined_footing`:
  - Centroide de la zapata trapezoidal centrado exactamente sobre la línea de acción de la resultante de cargas `P1 + P2` para anular momentos de excentricidad global.
  - Signos de momentos flectores y armadura corregidos, diferenciando la flexión negativa (hogging) en el vano entre pilares del vuelo en los extremos.
- `memos.zapata_corrida`: el dictamen global solo declara «CUMPLE» si todas las comprobaciones analíticas (incluyendo punzonamiento) resultan favorables.
- `services.walls`:
  - `bearing_FS` devolvía un 3,0 fijo («placeholder») que enmascaraba la falta de verificación geotécnica; ahora devuelve `None` explícito indicando que el servicio no evalúa la capacidad portante.
  - Brazos mecánicos de los momentos estabilizadores corregidos, asignando los pesos propios del fuste y del prisma de suelo sobre el talón a sus centros de gravedad reales.
- `codes.aci318_anchorage`: factor de reducción de resistencia φ para acero dúctil a cortante corregido a 0,65 según ACI 318-19 Tabla 17.5.3 (antes 0,75).
- `analysis.seismic.liquefaction_screening`: umbral de finos y golpeo según EN 1998-5 §4.1.4: limo > 35 % y N_1(60) > 20 eximen de análisis con aceleración reducida.
- `analysis.seismic.seismic_thrust`: el incremento dinámico de empuje activo con nivel freático no duplica el peso del agua al calcular la masa acelerada.
- `analysis.seismic_footing`: brazo de palanca para la inercia del bloque de zapata corregido a la mitad del canto `h/2` (antes canto entero `h`).
- `integration.fastsap_bridge`: no genera ni inventa reacciones de apoyo si no son suministradas explícitamente por el modelo exterior.
- `analysis.pile_lateral`: condiciones de contorno en cabeza para diferencias finitas convergentes a la solución analítica BVP de viga de Euler-Bernoulli sobre lecho elástico lineal (Reese en rango elástico).
- `analysis.cpt`: cálculo de tensión vertical total σ_v0 corregido considerando la densidad seca sobre el freático y sumergida bajo el freático; perfiles estratificados inician en la cota de superficie z = 0.
- `analysis.mat_foundation`: formulación de placa de Mindlin sobre muelles de Winkler corregida; contraste analítico con la solución de Hetényi para placa infinita bajo carga puntual y eliminación del patrón de damero numérico en losas gruesas.
- `design.gravity_wall`, `design.mse_wall` y `design.counterfort_wall`: empujes exteriores evaluados con ángulos de cálculo φ_d en conjuntos de parámetros STR/GEO; sobrecargas afectadas por γ_Q.
- `design.diaphragm_wall`: cálculo de fuerzas en puntales y momentos máximos derivados del equilibrio estático estricto respecto al pie o punto de rotación; rechazo explícito de cohesión o freático en métodos que no los modelan analíticamente.
- `design.buoyancy_check`: comprobación de subpresión UPL según EN 1997-1 exige un factor W/U ≥ 1/0,9 = 1,111 (antes bastaba 1,10).
- Versión unificada 1.1.0 en `pyproject.toml`, `foundationcalc.__version__` y la API FastAPI.

### Añadido

- `tests/test_fix_110_correcciones.py`: 37 tests dedicados a verificar cada corrección analítica con su oráculo independiente (integración numérica, soluciones de Hetényi y Das, comprobaciones manuales).
- 30 casos de uso ejecutables en `examples/` que cubren las 6 familias de capacidades del paquete, cada uno contrastado contra oráculos normativos o métodos independientes, con salida capturada en `examples/output/`.
- `tests/test_examples.py`: suite automatizada que ejecuta los 30 ejemplos como subprocesos aislados bajo CI.
- `README.md` reescrito con plantilla estructurada, tabla de capacidades y salidas de ejecución reales.

### Límites documentados (sin cambio de código)

- `services.bearing.bearing_capacity_multilayer`: módulo histórico y deprecado; no combina adecuadamente estratos múltiples para punzonamiento profundo. La calculadora canónica recomendada es `analysis.bearing_capacity`.
- `api.app`: el endpoint `/api/walls/cantilever` devuelve `bearing_FS = null` por diseño y debe complementarse con la verificación de hundimiento de `design.retaining_wall`.
- `design.combined_footing`: limitado a dos columnas alineadas; para baterías de pilares múltiples se requiere modelización como losa continua o viga flotante.
- `analysis.pile_lateral`: diferencias finitas formuladas para sección constante; variaciones bruscas de inercia requieren refinamiento de malla por tramos.
- `analysis.mat_foundation`: el esquema de despegue de Winkler es secante y converge para áreas en contacto mayores al 70 %; despegues severos requieren análisis elastoplástico de contacto.
