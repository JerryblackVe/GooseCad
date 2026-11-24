# 0.1.0-alpha.1 — 2026-11-24 (local, experimental)
Nuevo núcleo OCP: caja, cilindro, esfera, tres booleanas, validación y propiedades; tests, benchmarks, eliminación de validación redundante; experimento de historia de caras; CI propuesto y documentación inicial. No distribución ni release estable.

- GC-TOPO-01: resolver historia y roles cartesianos, detectar ambigüedad y eliminación.

GC-TOPO-02: fusiones, Generated, referencia JSON, 5 pruebas adicionales, benchmark y sonda OCAF aislada.

GC-DAG-01: DAG de estructura fija, Kahn determinista, índices de sucesores, invalidación transitiva y caché por nodo, evaluación de cambios en staging y publicación atómica bajo RLock; cancelación cooperativa entre operaciones. 34/34 pruebas locales (12 nuevas), 1500 muestras adicionales (2700 acumuladas). Contrato de resultados prestados de solo lectura; callbacks puros, no mutar TopoDS. Sin concurrencia del kernel, reconfiguración dinámica, persistencia general ni UI.

GC-DOC-01: Document posee Graph, edición por lote, revisión CAS, undo/redo con parches escalares inmutables, historial acotado configurable (100 por defecto), rollback ante fallo/cancelación, protección de reentrada y escrituras concurrentes serializadas. 45/45 pruebas locales (11 nuevas), 2400 muestras adicionales (5100 acumuladas). No almacenamiento en disco, edición estructural ni persistencia arbitraria; valores geométricos prestados de solo lectura. Deshacer/rehacer recalculan geometría en vez de guardar copias.

GC-DOC-02: formato nativo v1 JSON canónico con SHA-256, registro cerrado de seis operaciones OCCT, validación de tipos, referencias, ciclos, tamaño (2 MiB) y nodos (2048); guardado temporal mismo directorio, fsync, os.replace y fsync de directorio POSIX; copia .previous y recuperación explícita sin sobrescribir original. 63 pruebas aprobadas (18 nuevas), 720 muestras nuevas (5820 acumuladas).
