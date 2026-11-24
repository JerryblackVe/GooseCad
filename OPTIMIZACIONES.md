# Optimizaciones
O-001: revisar flujo booleano detectó doble BRepCheck_Analyzer del resultado; reutiliza validación interna sin omitir validación de entradas/resultados. Patch results/remove-revalidation.patch (revertir para reproducir baseline). Medianas seriales antes/después ms: union 7.9183/6.7923; cut 5.8748/5.3627; common 5.9358/5.4734. 10/10 pruebas antes y después y validación analítica en 900 muestras. Primitivas no modificadas; variación muestra ruido. No se midió perfil de CPU ni memoria; confirmar en más rondas. Paralelismo de modelos pequeños más lento; queda opt-in.

GC-TOPO-01: índice de pertenencia reutilizado, sin comparación contra implementación lineal; no se afirma aceleración.

GC-TOPO-02: índice de propietarios por índice de subforma para detectar N:1 en recorrido de candidatos; no comparación cuadrática de pares. Línea base medida, sin declarar mejora comparativa.

GC-DAG-01: evitar copia extra de set de afectados, precalcular orden de operaciones, ruta directa un argumento y evitar ordenar si todas están afectadas. Baseline/optimizado/repetición: cadena 10k mediana 5.024/3.068/3.192 ms incremental; full 3.935/2.039/2.189 ms. Ramas 10k incremental 0.0200/0.0315/0.0211 ms: ruido/regresión no concluyente, repetir en hardware controlado; no se afirma mejora universal. Patch reproducible results/dag-optimization.patch. El coste de descubrimiento cuando todo cambia sigue pendiente.
