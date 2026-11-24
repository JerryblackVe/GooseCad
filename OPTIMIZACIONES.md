# Optimizaciones
O-001: revisar flujo booleano detectó doble BRepCheck_Analyzer del resultado; reutiliza validación interna sin omitir validación de entradas/resultados. Patch results/remove-revalidation.patch (revertir para reproducir baseline). Medianas seriales antes/después ms: union 7.9183/6.7923; cut 5.8748/5.3627; common 5.9358/5.4734. 10/10 pruebas antes y después y validación analítica en 900 muestras. Primitivas no modificadas; variación muestra ruido. No se midió perfil de CPU ni memoria; confirmar en más rondas. Paralelismo de modelos pequeños más lento; queda opt-in.

GC-TOPO-01: índice de pertenencia reutilizado, sin comparación contra implementación lineal; no se afirma aceleración.

GC-TOPO-02: índice de propietarios por índice de subforma para detectar N:1 en recorrido de candidatos; no comparación cuadrática de pares. Línea base medida, sin declarar mejora comparativa.

GC-DAG-01: evitar copia extra de set de afectados, precalcular orden de operaciones, ruta directa un argumento y evitar ordenar si todas están afectadas. Baseline/optimizado/repetición: cadena 10k mediana 5.024/3.068/3.192 ms incremental; full 3.935/2.039/2.189 ms. Ramas 10k incremental 0.0200/0.0315/0.0211 ms: ruido/regresión no concluyente, repetir en hardware controlado; no se afirma mejora universal. Patch reproducible results/dag-optimization.patch. El coste de descubrimiento cuando todo cambia sigue pendiente.

GC-DOC-01: parches de parámetros, no copias B-Rep; se copia el historial acotado para asegurar publicación sin operaciones de usuario entre commits. Mediana edit con límite 100 antes/después guard de reentrada 4.750/4.627 µs, sin mejora atribuible por ruido. Límite 1000: 10.721 µs tras guard; estudiar estructura persistente solo si mediciones de modelos reales justifican complejidad.

GC-DOC-02: 3 rondas de 240 muestras, 1/20/100 cuerpos independientes. Se eliminó segunda validación de esquema en carga; no se demuestra mejora significativa de latencia. Ronda final: 100 cuerpos save 3.7126 ms, load 50.2768 ms (medianas). Resultados native-*.csv. Incluye fsync, excluye verificación posterior de benchmark; entorno compartido Linux, no extrapolar a Windows.

GC-SOLVER-01: 2 rondas de 240 muestras, 1/10/50 grupos de dos puntos con igualdad horizontal. Descomposición con SVD por grupo empeoró 50 grupos: 1.6238 ms vs 0.4359 ms global. Camino especializado final: 0.1995 ms vs 0.4502 ms global; comparación de medianas misma ronda. Residuos y coordenadas equivalentes dentro de tolerancia; no extrapolar a sistemas no lineales. Datos solver-partition-baseline.csv y solver-bench.csv.
