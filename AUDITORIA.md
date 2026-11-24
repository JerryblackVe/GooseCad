# Auditoría inicial
Cero código anterior importado. Se analizaron nueve capturas, no se copiaron recursos de Autodesk. No se transfirieron archivos. 10 tests aprobados dos veces, C++20 smoke OK, compileall OK, 900 muestras válidas. Historia topológica 1:N registrada. No auditoría de seguridad exhaustiva ni pruebas de concurrencia; acceso a TopoDS interno, límites de dimensión experimentales. Sin GUI, sin instalador, sin CI de esta revisión, licencias de distribución pendientes. Revisión de dependencias y hashes por plataforma pendiente.

Auditoría de formato: se normalizaron finales CRLF de CSV a LF; el contexto del patch conserva sus espacios por formato diff.

GC-TOPO-01: 17 pruebas aprobadas tras corrección de roles; fusión N:1, identidad tras recarga, orden alterado y OCAF no validados.

GC-TOPO-02: 22 pruebas locales aprobadas, 200 muestras. OCAF aislado 2 reproducciones exit 134; riesgo S1 experimental, no incluido en runtime/CI. Persistencia multietapa no verificada.

GC-DAG-01: DAG de estructura fija, Kahn determinista, índices de sucesores, invalidación transitiva y caché por nodo, evaluación de cambios en staging y publicación atómica bajo RLock; cancelación cooperativa entre operaciones. 34/34 pruebas locales (12 nuevas), 1500 muestras adicionales (2700 acumuladas). Contrato de resultados prestados de solo lectura; callbacks puros, no mutar TopoDS. Sin concurrencia del kernel, reconfiguración dinámica, persistencia general ni UI. Pruebas aleatorias deterministas (200 operaciones, 40 actualizaciones) contrastadas contra recálculo total; prueba de lectura concurrente, no equivale a validar concurrencia OCCT. OCAF sigue aislado.
