# Progreso
2026-11-24: lectura del protocolo, inspección de entorno y GitHub, 9 capturas, inventario inicial 301 registros, primer kernel OCP y pruebas; reducción de validación duplicada, dos mediciones y prueba de historial. CI redactado, no publicado. Ver results/ y ESTADO_PROYECTO.md.

GC-TOPO-01: roles de caja y resolución conservadora de historia OCCT, 7 pruebas nuevas; benchmark 100 muestras.

GC-TOPO-02: 22/22 tests locales; 200 muestras nuevas; CI base Windows/Linux verificado. OCAF pendiente por abort.

GC-DAG-01: DAG de estructura fija, Kahn determinista, índices de sucesores, invalidación transitiva y caché por nodo, evaluación de cambios en staging y publicación atómica bajo RLock; cancelación cooperativa entre operaciones. 34/34 pruebas locales (12 nuevas), 1500 muestras adicionales (2700 acumuladas). Contrato de resultados prestados de solo lectura; callbacks puros, no mutar TopoDS. Sin concurrencia del kernel, reconfiguración dinámica, persistencia general ni UI.

GC-DOC-01: Document posee Graph, edición por lote, revisión CAS, undo/redo con parches escalares inmutables, historial acotado configurable (100 por defecto), rollback ante fallo/cancelación, protección de reentrada y escrituras concurrentes serializadas. 45/45 pruebas locales (11 nuevas), 2400 muestras adicionales (5100 acumuladas). No almacenamiento en disco, edición estructural ni persistencia arbitraria; valores geométricos prestados de solo lectura. Deshacer/rehacer recalculan geometría en vez de guardar copias.

GC-DOC-02: formato nativo v1 JSON canónico con SHA-256, registro cerrado de seis operaciones OCCT, validación de tipos, referencias, ciclos, tamaño (2 MiB) y nodos (2048); guardado temporal mismo directorio, fsync, os.replace y fsync de directorio POSIX; copia .previous y recuperación explícita sin sobrescribir original. 63 pruebas aprobadas (18 nuevas), 720 muestras nuevas (5820 acumuladas).

GC-SOLVER-01: solucionador experimental 2D de puntos con horizontal, vertical, coincidencia, fijación y distancia. Igualdades lineales consistentes mediante unión de componentes escalares y proyección; fallback SVD/lstsq para anclajes en conflicto; distancia no lineal mediante SciPy TRF y Jacobiano analítico; residuos ≤1e-7 mm, estimación DOF y filas dependientes. 78 pruebas aprobadas (15 nuevas), 480 muestras adicionales (6300 acumuladas).


GC-ABI-01: prueba C/C++ escalar independiente, ABI v1, IDs monotónicos, registro acotado, propiedad explícita create/release, errores enteros y noexcept, consulta por lote validada antes de escribir. GCC/CMake Release y ASan/UBSan con CTest aprobados; 10.000 ciclos de vida; 78 pruebas Python aprobadas. 200 muestras ctypes (256 consultas, mediana escalar 0.1373635 ms, lote 0.002274 ms). No incluye Goose ni OCCT; no es benchmark del kernel. Goose no instalado, SDK C++ OCCT ausente, DNS bloqueado. Buffers válidos/no solapados a cargo del llamador, IDs locales al proceso/biblioteca, mutex global, no se ha probado concurrencia ni FFI Goose. CI CMake Windows/Linux preparado, aún no ejecutado para este commit. Siguiente GC-GEO-02: perfiles de boceto resueltos, extrusión/revolución B-Rep.
