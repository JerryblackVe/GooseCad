# Pendientes
P0 publicación autorizada; verificar escritura y remoto; CI Windows; resolver identidad Goose, instalar compilador y probar ABI; SDK C++ OCCT; naming 1:N, N:1 y referencias eliminadas; solver; DAG; casos booleanos complejos y precisión extrema; matriz exhaustiva por comando y variantes. P1 GUI, documentos, STEP y demás criterios alpha funcional. No se afirma paridad.

GC-BOOT/GC-TOPO-01 sincronizados y CI aprobado. GC-TOPO-02 parcial; pendiente persistencia multietapa, OCAF, DAG.

GC-DAG-01 fijo verificado localmente; pendientes edición estructural, caché limitada y concurrencia, snapshots de UI, cancelación interna de OCCT, GC-DOC-01, GC-SOLVER-01 y OCAF.

GC-DOC-01 parámetros/undo/redo verificado localmente; faltan persistencia, transacciones estructurales, historial de memoria limitada por bytes, UI asíncrona y seguridad de importación.

Limitaciones: escritor único por ruta con coordinación externa; Windows sin fsync portable de directorio; no prueba de corte eléctrico real, ni sandbox de OCCT, ni autenticación criptográfica; el checksum detecta daños accidentales. La copia previa se valida estructuralmente, no se reconstruye durante guardado. No se persisten historial undo/redo, referencias topológicas generales, bocetos, ensamblajes ni B-Rep arbitrario. Solo parámetros numéricos y DAG fijo; dependencias repetidas no admitidas. El fallo posterior a replace puede indicar guardado efectuado con durabilidad no confirmada. No abrir documentos no confiables sin aislamiento futuro.

Límites: 256 puntos, 512 restricciones, dominio de coordenadas ±1e6 mm, máximo 200 evaluaciones no lineales, rango local no prueba redundancia global. Una falta de convergencia no demuestra contradicción no lineal; degeneración de puntos coincidentes se informa como unresolved. No hay curvas, tangencias, ángulos, arcos, cotas generales ni integración con bocetos, DAG o formato v1; tampoco cancelación, análisis de memoria o paralelismo seguro. Comparaciones en Linux con un hilo BLAS.
