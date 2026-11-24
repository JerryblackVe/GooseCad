# Progreso
2026-11-24: lectura del protocolo, inspección de entorno y GitHub, 9 capturas, inventario inicial 301 registros, primer kernel OCP y pruebas; reducción de validación duplicada, dos mediciones y prueba de historial. CI redactado, no publicado. Ver results/ y ESTADO_PROYECTO.md.

GC-TOPO-01: roles de caja y resolución conservadora de historia OCCT, 7 pruebas nuevas; benchmark 100 muestras.

GC-TOPO-02: 22/22 tests locales; 200 muestras nuevas; CI base Windows/Linux verificado. OCAF pendiente por abort.

GC-DAG-01: DAG de estructura fija, Kahn determinista, índices de sucesores, invalidación transitiva y caché por nodo, evaluación de cambios en staging y publicación atómica bajo RLock; cancelación cooperativa entre operaciones. 34/34 pruebas locales (12 nuevas), 1500 muestras adicionales (2700 acumuladas). Contrato de resultados prestados de solo lectura; callbacks puros, no mutar TopoDS. Sin concurrencia del kernel, reconfiguración dinámica, persistencia general ni UI.
