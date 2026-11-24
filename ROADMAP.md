# Hoja de ruta
0 preparación (checkpoint remoto pendiente); 1 riesgos: naming, solver, FFI y Windows; 2 geometría y STEP; 3 documentos, grafo, transacciones; 4 bocetos; 5 visor y UI accesible; 6 sólidos y superficies avanzados; 7 ensamblajes; 8 chapa/malla/forma/planos/render/animación/CAM/CAE/generativo/electrónica; 9 optimización y auditoría global; 10 instalador Win10/11 x64; 11 mantenimiento. El rendimiento se mide en todas las fases. No se fijan fechas sin evidencia.

GC-SKETCH-02: documentos v1/v2, bocetos poligonales declarativos y barridos B-Rep; consultar docs/FORMATO_NATIVO.md. CI previo Windows/Linux aprobado; nuevo CI pendiente. No es aplicación de escritorio.

GC-DOC-03: guardado con bloqueo cooperativo y token de revisión de disco; ver docs/FORMATO_NATIVO.md. Pruebas locales aprobadas; verificar CI Windows/Linux.


GC-SKETCH-03: formato v3 y regiones curvas exactas; siguiente GC-MESH-01.


GC-MESH-01: adaptador de teselación previo al visor; siguiente GC-MESH-02.


GC-MESH-02: caché LRU por instancia de documento, cuerpo, revisión de nodo y configuración completa. DAG publica sello junto al valor en la misma transacción. 151 pruebas locales (9 nuevas), 120 muestras de caché y 400 de regresión DAG (8790 acumuladas). 20 esferas: reconstrucción 118.6522 ms, edición de una 6.4281 ms, caliente 0.02764 ms; buffers equivalentes exactos entre caché y directo, ~492752 bytes contabilizados en última muestra. No es FPS. Presupuesto por buffers y offsets más límite de entradas; excluye overhead completo, memoria OCCT/GPU y referencias externas. Snapshots prestados de solo lectura (incluida metadata NumPy), bytes inmutables, comprobar is_current antes de presentar/seleccionar. Reload/recovery crea nueva caché. Misses simultáneos pueden duplicar trabajo; no se garantiza ejecución concurrente OCCT, snapshots viejos no son hits actuales. No hay persistencia de mallas ni selección topológica persistente.
