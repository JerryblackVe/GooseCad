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


GC-ABI-01: prueba C/C++ escalar independiente, ABI v1, IDs monotónicos, registro acotado, propiedad explícita create/release, errores enteros y noexcept, consulta por lote validada antes de escribir. GCC/CMake Release y ASan/UBSan con CTest aprobados; 10.000 ciclos de vida; 78 pruebas Python aprobadas. 200 muestras ctypes (256 consultas, mediana escalar 0.1373635 ms, lote 0.002274 ms). No incluye Goose ni OCCT; no es benchmark del kernel. Goose no instalado, SDK C++ OCCT ausente, DNS bloqueado. Buffers válidos/no solapados a cargo del llamador, IDs locales al proceso/biblioteca, mutex global, no se ha probado concurrencia ni FFI Goose. CI CMake Windows/Linux preparado, aún no ejecutado para este commit. Siguiente GC-GEO-02: perfiles de boceto resueltos, extrusión/revolución B-Rep.


GC-GEO-02: perfiles XY cerrados de 3–256 puntos integrados con solver y DAG; extrusión ±Z y revolución parcial/completa alrededor de Y con perfil estrictamente X positivo. Construcción OCCT exacta, validación de aristas/contorno/cara/sólido, rechazo de cruces, contactos, aristas degeneradas y adyacentes casi colineales. 89 pruebas Python aprobadas (11 nuevas), incluyendo cotas de distancia, volumen/superficie/centro analíticos, orientación, concavidad, rollback y comparación de validación exhaustiva vs cajas delimitadoras. 560 muestras nuevas (7060 acumuladas). Para 256 vértices: validación exhaustiva 51.026 ms vs cajas 2.373 ms (medianas misma ronda); extrusión 72.270 ms. Revolución 4 vértices 0.984 ms, 32 vértices 6.419 ms; se eliminó revalidación del mismo perfil, sin atribuir mejora concluyente a la comparación entre rondas. Límites: sin agujeros, curvas, perfiles múltiples, colinealidad adyacente, eje configurable, caras sobre eje, barridos generales ni persistencia v1; perfil bajo restringido permitido con DOF explícito. No se integra en UI. No se modifica formato nativo. GC-ABI-01 Goose/OCCT bloqueado, prototipo C/C++ aprobado localmente. CI solver aprobado (45489908118), ABI pendiente de resultado al registrar. Siguiente GC-SKETCH-02: integración de operaciones declarativas y almacenamiento versionado de bocetos y barridos; preservar lectura v1 y pruebas de recuperación, no migrar destructivamente.

GC-SKETCH-02: primera ejecución del benchmark abortó por factor 2 incorrecto en fórmula analítica de revolución parcial; corregida a π((1+w)^2−1) para altura 4 y ángulo π/2. Ambas rondas finales validan volúmenes, bytes y nodos evaluados. OCAF S1 permanece abierto.

GC-DOC-03: se endureció retirada de lock con verificación de identidad del descriptor; regresión POSIX de sidecar sustituido aprobada. Proceso muerto deja bloqueo por diseño; recuperación manual documentada. Riesgo de limpieza post-replace y escritor externo abierto; no afirmar protección universal.
