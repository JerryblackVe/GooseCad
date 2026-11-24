# GooseCAD Professional — 0.1.0-alpha.1
Inicio limpio revisión 3.0. Núcleo experimental B-Rep, no aplicación de escritorio ni instalador todavía.
Repositorio oficial: https://github.com/JerryblackVe/GooseCad. Rama de trabajo feature/000-clean-start; publicación de código y documentación autorizada, excluyendo datos privados y medios del usuario.

Python 3.13.5 y OCCT nativo mediante OCP. Ejecutar desde la raíz:
```
python -m pip install -r dependencies/requirements-core.txt
python -m pip install --no-deps .
python -m unittest discover -s tests -v
python benchmarks/kernel_bench.py benchmark-local.csv
python experiments/topology_history.py
```
Ver ESTADO_PROYECTO.md, CONTINUIDAD.md, SIGUIENTE_PASO.md y PROMPT_MAESTRO.md. No se incorporó código anterior.

GC-SKETCH-02: documentos v1/v2, bocetos poligonales declarativos y barridos B-Rep; consultar docs/FORMATO_NATIVO.md. CI previo Windows/Linux aprobado; nuevo CI pendiente. No es aplicación de escritorio.

GC-DOC-03: guardado con bloqueo cooperativo y token de revisión de disco; ver docs/FORMATO_NATIVO.md. Pruebas locales aprobadas; verificar CI Windows/Linux.


GC-SKETCH-03: formato v1/v2/v3, regiones curvas y barridos exactos. Ver docs/FORMATO_NATIVO.md y SIGUIENTE_PASO.md.


GC-MESH-01: adaptador B-Rep a buffers de visualización, no cambia geometría exacta.


GC-MESH-02: caché LRU por instancia de documento, cuerpo, revisión de nodo y configuración completa. DAG publica sello junto al valor en la misma transacción. 151 pruebas locales (9 nuevas), 120 muestras de caché y 400 de regresión DAG (8790 acumuladas). 20 esferas: reconstrucción 118.6522 ms, edición de una 6.4281 ms, caliente 0.02764 ms; buffers equivalentes exactos entre caché y directo, ~492752 bytes contabilizados en última muestra. No es FPS. Presupuesto por buffers y offsets más límite de entradas; excluye overhead completo, memoria OCCT/GPU y referencias externas. Snapshots prestados de solo lectura (incluida metadata NumPy), bytes inmutables, comprobar is_current antes de presentar/seleccionar. Reload/recovery crea nueva caché. Misses simultáneos pueden duplicar trabajo; no se garantiza ejecución concurrente OCCT, snapshots viejos no son hits actuales. No hay persistencia de mallas ni selección topológica persistente.


GC-VIEW-01 (experimental): `python -m goosecad.view` abre el ejemplo de caja; `python -m goosecad.view archivo.gcad id_cuerpo [id_cuerpo2 ...]` abre un documento existente de confianza en modo solo visualización. Ratón trackball, R ajustar cámara, P seleccionar bajo cursor (ID de cara local impreso en terminal, resalta cuerpo), Q salir. VTK 9.6.2 ya incluido en requirements-core. Linux Xvfb/EGL comprobados; ventana Windows física no comprobada. Prueba gráfica Linux: `xvfb-run -a env GC_RENDER_TESTS=1 GC_INTERACT_TESTS=1 PYTHONPATH=src python -m unittest discover -s tests -p test_view.py -v`.
