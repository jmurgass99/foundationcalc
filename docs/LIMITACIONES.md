# Limitaciones conocidas de foundationcalc

Lo que el paquete no hace o hace de forma simplificada.

- **Capacidad portante multicapa**: `services.bearing.bearing_capacity_multilayer` (y `/api/bearing/multilayer`) con el método por defecto evalúa solo el estrato de apoyo, la vía deprecada; con `method="meyerhof_hanna"` delega en `analysis.multi_layer_bc` y comprueba el punzonamiento del estrato inferior (Meyerhof y Hanna, 1978), sin contrastar aquí con un caso publicado. El caso de la API muestra la diferencia: 1975 frente a 195 kPa con 0,3 m de arena sobre arcilla blanda.
- **Predimensionado de muros en la API**: `/api/walls/cantilever` devuelve `bearing_FS = null` salvo con `evaluate_bearing = true`, que pasa por `CantileverWallDesigner` (EN 1997-1). Ese `bearing_FS` es q_Rd/q_Ed con valores ya de cálculo: cumple si es ≥ 1, no es un factor global comparable a 3. Los FS de deslizamiento y vuelco siguen siendo los globales de Rankine.
- **Zapatas combinadas**: el módulo actual diseña zapatas de dos columnas; configuraciones complejas de tres o más pilares alineados deben modelarse mediante vigas continuas sobre lecho elástico o losas de cimentación.
- **Diferencias finitas en pilotes laterales**: la formulación implementada en `pile_lateral` modela pilotes de sección constante; variaciones escalonadas de inercia o estratigrafías con inversión brusca de rigidez deben discretizarse con mallas refinadas.
- **Losa de cimentación Mindlin**: el análisis elastoplástico de despegue en `analysis.mat_foundation` utiliza un esquema de rigidez secante en los muelles de Winkler que converge para despegues moderados (< 30 % de área); despegues severos requieren análisis no lineal con contacto de fricción en software especializado.
