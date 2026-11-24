# Fuentes consultadas — 2026-11-24
- Autodesk: https://help.autodesk.com/view/fusion360/ENU/ y https://help.autodesk.com/cloudhelp/ENU/Fusion-GetStarted/files/GS-WORKSPACES.htm (ámbitos de trabajo; inventario inicial).
- Autodesk sólidos: https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-CREATE-SOLID-FROM-SKETCH.htm
- Autodesk restricciones: https://help.autodesk.com/cloudhelp/ENU/Fusion-Sketch/files/SKT-CONSTRAINTS.htm
- Autodesk construcción: https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-CONSTRUCT-TOOLS.htm
- Autodesk ensamblaje: https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/CONSTRAIN-COMPONENTS-REF.htm
- Goose (candidato, identidad exacta a confirmar): https://github.com/aardappel/goose ; https://aardappel.github.io/goose/ ; genera C y tiene FFI C. Apache-2.0. No instalado ni probado. Distinto de Go y goose-lang/goose.
- OCCT: https://www.occt3d.com/dev/doc/overview/html/specification__boolean_operations.html (historial de booleanas; no garantiza naming persistente).
- OCP: https://github.com/CadQuery/OCP ; https://pypi.org/project/cadquery-ocp/7.9.3.1.1/ (wheel CPython 3.13 Windows x64 existente; no probado).
- CadQuery: https://github.com/CadQuery/cadquery (no se usa su API).
- CI: https://docs.github.com/en/actions/tutorials/build-and-test-code/python ; https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job
No se completó auditoría documental de cada comando ni se verificaron todas las dependencias potenciales. Referencias genéricas de la matriz son puntos de partida, no pruebas de cada función.

GC-SOLVER-01: SciPy 1.17.0 least_squares (TRF, Jacobiano analítico): https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.optimize.least_squares.html ; licencias SciPy/NumPy/SolveSpace: ver LICENCIAS.md. Consulta 2026-11-24. No se incorpora código de SolveSpace.

GC-ABI-01: https://aardappel.github.io/goose/ y https://github.com/aardappel/goose (C/extern fn, Apache-2.0, candidato sin instalación); https://www.occt3d.com/dev/doc/overview/html/occt_user_guides__modeling_algos.html (referencia modelado).
