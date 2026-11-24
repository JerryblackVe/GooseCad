# ADR
001 Python 3.13 + OCP para experimentar y avanzar con OCCT real; C++20 para futura ABI y partes calientes tras medir. Goose (candidato aardappel/goose) no probado ni obligatorio en ruta crítica. 002 ejecución serial por defecto en booleanas simples: medición local muestra sobrecoste de paralelismo. 003 B-Rep validado y unidades mm, sin fast-math ni aproximación de malla. 004 nombres topológicos deben conservar procedencia y detectar ambigüedad; índices descartados. 005 GitHub público: no publicación antes de confirmación, copia de emergencia; no borrar historial. 006 licencia propia pendiente de titular. 007 arquitectura y versiones no definitivas, dependencias CI sujetas a prueba.

GC-TOPO-01: no resolver automáticamente divisiones 1:N; roles semánticos de primitivas separados de identidad OCCT.

ADR-004: no resolver automáticamente fusiones N:1, ni usar Generated como reemplazo. Mantener identificadores semánticos de feature y roles; JSON schema 1 solo para referencias, no formato CAD final. OCAF no aprobado por fallo de ciclo de vida.

ADR-GC-DAG-01: estructura fija y callbacks puros con valores prestados; cambios estructurales se harán por reconstrucción transaccional. No copiar geometría ni snapshot completo por edición. Se prioriza atomicidad y exactitud sobre paralelismo no validado.

ADR-GC-DOC-01: solo escalares JSON finitos como entradas; funciones de cálculo puras y registro privado de parches. Revisiones monotónicas, incluso undo/redo; no guardar código ejecutable en documentos. Historial limitado por entradas, no por memoria.
