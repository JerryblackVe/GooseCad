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
