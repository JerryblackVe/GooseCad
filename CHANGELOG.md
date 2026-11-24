# 0.1.0-alpha.1 — 2026-11-24 (local, experimental)
Nuevo núcleo OCP: caja, cilindro, esfera, tres booleanas, validación y propiedades; tests, benchmarks, eliminación de validación redundante; experimento de historia de caras; CI propuesto y documentación inicial. No distribución ni release estable.

- GC-TOPO-01: resolver historia y roles cartesianos, detectar ambigüedad y eliminación.

GC-TOPO-02: fusiones, Generated, referencia JSON, 5 pruebas adicionales, benchmark y sonda OCAF aislada.

GC-DAG-01: DAG de estructura fija, Kahn determinista, índices de sucesores, invalidación transitiva y caché por nodo, evaluación de cambios en staging y publicación atómica bajo RLock; cancelación cooperativa entre operaciones. 34/34 pruebas locales (12 nuevas), 1500 muestras adicionales (2700 acumuladas). Contrato de resultados prestados de solo lectura; callbacks puros, no mutar TopoDS. Sin concurrencia del kernel, reconfiguración dinámica, persistencia general ni UI.
