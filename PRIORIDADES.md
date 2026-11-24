# Prioridades
P0 GC-BOOT: privacidad y sincronización; GC-TOPO-01 naming persistente (experimento inicial hecho); GC-ABI-01 C++ SDK/Goose FFI; GC-SOLVER-01 restricciones; GC-DAG-01 recálculo incremental; GC-DOC-01 transacciones/persistencia; GC-PERF-01 escalabilidad, concurrencia y tolerancias; CI Windows. P1 primitivas, extrusión, revolución, booleanas, visor, boceto, STEP. P2 superficies/ensamblajes, P3 espacios especializados, P4 automatización. Rendimiento, seguridad, integridad y accesibilidad transversales.

GC-TOPO-02 parcial verificado; GC-DAG-01 siguiente. GC-OCAF-01 bloquea persistencia general, no grafo independiente.

GC-DAG-01 parcial verificado. Próximo GC-DOC-01: transacciones de entrada, undo/redo con límites y revisión; formato persistente y guardado atómico después. GC-SOLVER-01 y GC-ABI-01 siguen P0.

GC-DOC-01 parcial verificado localmente. GC-DOC-02 siguiente: formato mínimo versionado, operaciones identificadas por registro permitido, guardado atómico y recuperación; después GC-SOLVER-01, GC-ABI-01. Sin integración OCAF hasta resolver S1.

GC-DOC-02 parcial verificado localmente; siguiente GC-SOLVER-01 (P0); luego GC-ABI-01. Pendiente bloqueo por archivo, aislamiento de cargas, estrés de persistencia y durabilidad Windows.

GC-SOLVER-01 parcial verificado localmente; siguiente GC-ABI-01 (P0), luego integración de bocetos y solucionador, persistencia estructural y GC-GEO-02. Pendientes solver de curvas, convergencia, escalabilidad y diagnóstico.


GC-ABI-01: prueba C/C++ escalar independiente, ABI v1, IDs monotónicos, registro acotado, propiedad explícita create/release, errores enteros y noexcept, consulta por lote validada antes de escribir. GCC/CMake Release y ASan/UBSan con CTest aprobados; 10.000 ciclos de vida; 78 pruebas Python aprobadas. 200 muestras ctypes (256 consultas, mediana escalar 0.1373635 ms, lote 0.002274 ms). No incluye Goose ni OCCT; no es benchmark del kernel. Goose no instalado, SDK C++ OCCT ausente, DNS bloqueado. Buffers válidos/no solapados a cargo del llamador, IDs locales al proceso/biblioteca, mutex global, no se ha probado concurrencia ni FFI Goose. CI CMake Windows/Linux preparado, aún no ejecutado para este commit. Siguiente GC-GEO-02: perfiles de boceto resueltos, extrusión/revolución B-Rep.
