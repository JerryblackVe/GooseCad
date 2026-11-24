# Reproducir
Python 3.13.5 y entorno virtual; `python -m pip install -r dependencies/requirements-core.txt` y `python -m pip install --no-deps .`; `python -m compileall -q src tests benchmarks experiments`; `python -m unittest discover -s tests -v`; `python benchmarks/kernel_bench.py benchmark-local.csv`; `python experiments/topology_history.py`. En Linux actual se ejecutó con PYTHONPATH=src y paquetes preinstalados (sin instalación nueva). Compilador smoke: `g++ -std=c++20 -O2 -Wall -Wextra -Werror experiments/compiler_smoke.cpp -o /tmp/gc-smoke && /tmp/gc-smoke`. No es compilación de OCCT C++ ni del CAD completo. C++ SDK y toolchain MSVC pendientes.

GC-SKETCH-02: documentos v1/v2, bocetos poligonales declarativos y barridos B-Rep; consultar docs/FORMATO_NATIVO.md. CI previo Windows/Linux aprobado; nuevo CI pendiente. No es aplicación de escritorio.

GC-DOC-03: guardado con bloqueo cooperativo y token de revisión de disco; ver docs/FORMATO_NATIVO.md. Pruebas locales aprobadas; verificar CI Windows/Linux.


Benchmark curvas: `PYTHONPATH=src OPENBLAS_NUM_THREADS=1 python benchmarks/curve_bench.py curves-local.csv --repetitions 30`.


Benchmark malla: `PYTHONPATH=src OPENBLAS_NUM_THREADS=1 python benchmarks/mesh_bench.py mesh-local.csv --repetitions 20`.


GC-MESH-02: caché LRU por instancia de documento, cuerpo, revisión de nodo y configuración completa. DAG publica sello junto al valor en la misma transacción. 151 pruebas locales (9 nuevas), 120 muestras de caché y 400 de regresión DAG (8790 acumuladas). 20 esferas: reconstrucción 118.6522 ms, edición de una 6.4281 ms, caliente 0.02764 ms; buffers equivalentes exactos entre caché y directo, ~492752 bytes contabilizados en última muestra. No es FPS. Presupuesto por buffers y offsets más límite de entradas; excluye overhead completo, memoria OCCT/GPU y referencias externas. Snapshots prestados de solo lectura (incluida metadata NumPy), bytes inmutables, comprobar is_current antes de presentar/seleccionar. Reload/recovery crea nueva caché. Misses simultáneos pueden duplicar trabajo; no se garantiza ejecución concurrente OCCT, snapshots viejos no son hits actuales. No hay persistencia de mallas ni selección topológica persistente.
