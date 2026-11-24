# Windows x64
Instalar CPython 3.13.5 x64 y Git; en PowerShell crear entorno `py -3.13 -m venv .venv`, activar o usar `.venv/Scripts/python.exe`, ejecutar pasos de INSTRUCCIONES_COMPILACION.md. CI `.github/workflows/kernel-ci.yml` preparado para windows-2022 y ubuntu-24.04. Versiones acciones por major tag, fijar SHA tras auditoría. No publicado ni ejecutado para esta revisión; wheel OCP Windows disponible según PyPI, instalación no verificada. Próximo MSVC/CMake/SDK OCCT; instalador Inno Setup/WiX/NSIS por seleccionar. No hay ejecutable ni instalador actual.

GC-SKETCH-02: documentos v1/v2, bocetos poligonales declarativos y barridos B-Rep; consultar docs/FORMATO_NATIVO.md. CI previo Windows/Linux aprobado; nuevo CI pendiente. No es aplicación de escritorio.

GC-DOC-03: guardado con bloqueo cooperativo y token de revisión de disco; ver docs/FORMATO_NATIVO.md. Pruebas locales aprobadas; verificar CI Windows/Linux.
