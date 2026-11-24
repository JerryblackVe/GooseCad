# Registro de defectos y bloqueos
B-001 P0 repo público sin confirmación de publicación. B-002 P0 DNS desde terminal, no instalación ni Git remoto. B-003 P0 Goose y SDK OCCT C++ ausentes. B-004 Windows sin probar. R-001 alto riesgo: división de cara 1:N con Modified/Generated; no confundir índice con identidad. O-001 coste de validación repetida corregido, patch y dos benchmarks. Sin fallos de tests registrados; no equivale a ausencia de defectos críticos. R-002 dominio geométrico experimental ±1e6 mm; geometrías degeneradas, tolerancias extremas, manejo exhaustivo de excepciones OCCT y entradas no tipadas pendientes.

O-002: se corrigieron avisos de whitespace por finales CRLF de CSV; sin alteración de valores.

B-001 privacidad resuelto por autorización expresa. Reproducción: importación fallida sin instalar paquete; PYTHONPATH=src resolvió, 10/10 OK.

GC-TOPO-01: primera prueba de eliminación falló por nombres OCCT Left/Front no coincidentes con ejes; corregido mapeo, prueba de centroides añadida. 17/17 OK.

GC-OCAF-01 (S1 experimental): TDF_Data/TNaming devuelve cara correcta pero proceso aborta en destrucción con Standard_NullObject, exit 134. Repro: experiments/ocaf_probe.py en proceso aislado; no ejecutarlo en CI normal. Investigar propiedad/orden de destrucción y documento TDocStd antes de integrar.

GC-DAG-PERF-01 (abierto, rendimiento): cadena con todos los nodos afectados es más lenta que full por descubrimiento de descendientes; ramas 10k ruido entre rondas. Medir bajo hardware controlado y estudiar estrategias adaptativas. GC-OCAF-01 sigue abierto.

GC-DOC-REENTRY-01 (corregido): durante conversión de Mapping, código de usuario podía reentrar antes de activar guard; ahora se rechaza desde inicio de edición, con prueba de regresión. OCAF y GC-DAG-PERF-01 siguen abiertos.

GC-DOC-02: detectada posible colisión con nombre de recuperación; sufijo .previous reservado y prueba de regresión aprobada. GC-OCAF-01 sigue abierto y aislado.

GC-SOLVER-01: los resultados de NumPy inicialmente eran numpy.float64 y la validación de entrada los rechazaba; corregido a float nativo y regresión de reutilización aprobada. La descomposición con SVD por grupo resultó más lenta, sustituida en igualdades consistentes por algoritmo especializado. GC-OCAF-01 sigue aislado.
