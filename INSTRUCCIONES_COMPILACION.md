# Reproducir
Python 3.13.5 y entorno virtual; `python -m pip install -r dependencies/requirements-core.txt` y `python -m pip install --no-deps .`; `python -m compileall -q src tests benchmarks experiments`; `python -m unittest discover -s tests -v`; `python benchmarks/kernel_bench.py benchmark-local.csv`; `python experiments/topology_history.py`. En Linux actual se ejecutó con PYTHONPATH=src y paquetes preinstalados (sin instalación nueva). Compilador smoke: `g++ -std=c++20 -O2 -Wall -Wextra -Werror experiments/compiler_smoke.cpp -o /tmp/gc-smoke && /tmp/gc-smoke`. No es compilación de OCCT C++ ni del CAD completo. C++ SDK y toolchain MSVC pendientes.

GC-SKETCH-02: documentos v1/v2, bocetos poligonales declarativos y barridos B-Rep; consultar docs/FORMATO_NATIVO.md. CI previo Windows/Linux aprobado; nuevo CI pendiente. No es aplicación de escritorio.

GC-DOC-03: guardado con bloqueo cooperativo y token de revisión de disco; ver docs/FORMATO_NATIVO.md. Pruebas locales aprobadas; verificar CI Windows/Linux.
