# ADR
001 Python 3.13 + OCP para experimentar y avanzar con OCCT real; C++20 para futura ABI y partes calientes tras medir. Goose (candidato aardappel/goose) no probado ni obligatorio en ruta crítica. 002 ejecución serial por defecto en booleanas simples: medición local muestra sobrecoste de paralelismo. 003 B-Rep validado y unidades mm, sin fast-math ni aproximación de malla. 004 nombres topológicos deben conservar procedencia y detectar ambigüedad; índices descartados. 005 GitHub público: no publicación antes de confirmación, copia de emergencia; no borrar historial. 006 licencia propia pendiente de titular. 007 arquitectura y versiones no definitivas, dependencias CI sujetas a prueba.

GC-TOPO-01: no resolver automáticamente divisiones 1:N; roles semánticos de primitivas separados de identidad OCCT.

ADR-004: no resolver automáticamente fusiones N:1, ni usar Generated como reemplazo. Mantener identificadores semánticos de feature y roles; JSON schema 1 solo para referencias, no formato CAD final. OCAF no aprobado por fallo de ciclo de vida.

ADR-GC-DAG-01: estructura fija y callbacks puros con valores prestados; cambios estructurales se harán por reconstrucción transaccional. No copiar geometría ni snapshot completo por edición. Se prioriza atomicidad y exactitud sobre paralelismo no validado.

ADR-GC-DOC-01: solo escalares JSON finitos como entradas; funciones de cálculo puras y registro privado de parches. Revisiones monotónicas, incluso undo/redo; no guardar código ejecutable en documentos. Historial limitado por entradas, no por memoria.

Limitaciones: escritor único por ruta con coordinación externa; Windows sin fsync portable de directorio; no prueba de corte eléctrico real, ni sandbox de OCCT, ni autenticación criptográfica; el checksum detecta daños accidentales. La copia previa se valida estructuralmente, no se reconstruye durante guardado. No se persisten historial undo/redo, referencias topológicas generales, bocetos, ensamblajes ni B-Rep arbitrario. Solo parámetros numéricos y DAG fijo; dependencias repetidas no admitidas. El fallo posterior a replace puede indicar guardado efectuado con durabilidad no confirmada. No abrir documentos no confiables sin aislamiento futuro.

Límites: 256 puntos, 512 restricciones, dominio de coordenadas ±1e6 mm, máximo 200 evaluaciones no lineales, rango local no prueba redundancia global. Una falta de convergencia no demuestra contradicción no lineal; degeneración de puntos coincidentes se informa como unresolved. No hay curvas, tangencias, ángulos, arcos, cotas generales ni integración con bocetos, DAG o formato v1; tampoco cancelación, análisis de memoria o paralelismo seguro. Comparaciones en Linux con un hilo BLAS.
