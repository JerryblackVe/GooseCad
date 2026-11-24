# Progreso
2026-11-24: lectura del protocolo, inspección de entorno y GitHub, 9 capturas, inventario inicial 301 registros, primer kernel OCP y pruebas; reducción de validación duplicada, dos mediciones y prueba de historial. CI redactado, no publicado. Ver results/ y ESTADO_PROYECTO.md.

GC-TOPO-01: roles de caja y resolución conservadora de historia OCCT, 7 pruebas nuevas; benchmark 100 muestras.

GC-TOPO-02: 22/22 tests locales; 200 muestras nuevas; CI base Windows/Linux verificado. OCAF pendiente por abort.

GC-DAG-01: DAG de estructura fija, Kahn determinista, índices de sucesores, invalidación transitiva y caché por nodo, evaluación de cambios en staging y publicación atómica bajo RLock; cancelación cooperativa entre operaciones. 34/34 pruebas locales (12 nuevas), 1500 muestras adicionales (2700 acumuladas). Contrato de resultados prestados de solo lectura; callbacks puros, no mutar TopoDS. Sin concurrencia del kernel, reconfiguración dinámica, persistencia general ni UI.

GC-DOC-01: Document posee Graph, edición por lote, revisión CAS, undo/redo con parches escalares inmutables, historial acotado configurable (100 por defecto), rollback ante fallo/cancelación, protección de reentrada y escrituras concurrentes serializadas. 45/45 pruebas locales (11 nuevas), 2400 muestras adicionales (5100 acumuladas). No almacenamiento en disco, edición estructural ni persistencia arbitraria; valores geométricos prestados de solo lectura. Deshacer/rehacer recalculan geometría en vez de guardar copias.
