# Windows x64
Instalar CPython 3.13.5 x64 y Git; en PowerShell crear entorno `py -3.13 -m venv .venv`, activar o usar `.venv/Scripts/python.exe`, ejecutar pasos de INSTRUCCIONES_COMPILACION.md. CI `.github/workflows/kernel-ci.yml` preparado para windows-2022 y ubuntu-24.04. Versiones acciones por major tag, fijar SHA tras auditoría. No publicado ni ejecutado para esta revisión; wheel OCP Windows disponible según PyPI, instalación no verificada. Próximo MSVC/CMake/SDK OCCT; instalador Inno Setup/WiX/NSIS por seleccionar. No hay ejecutable ni instalador actual.

GC-SKETCH-02: documentos v1/v2, bocetos poligonales declarativos y barridos B-Rep; consultar docs/FORMATO_NATIVO.md. CI previo Windows/Linux aprobado; nuevo CI pendiente. No es aplicación de escritorio.

GC-DOC-03: guardado con bloqueo cooperativo y token de revisión de disco; ver docs/FORMATO_NATIVO.md. Pruebas locales aprobadas; verificar CI Windows/Linux.


GC-VIEW-01 (experimental): `python -m goosecad.view` abre el ejemplo de caja; `python -m goosecad.view archivo.gcad id_cuerpo [id_cuerpo2 ...]` abre un documento existente de confianza en modo solo visualización. Ratón trackball, R ajustar cámara, P seleccionar bajo cursor (ID de cara local impreso en terminal, resalta cuerpo), Q salir. VTK 9.6.2 ya incluido en requirements-core. Linux Xvfb/EGL comprobados; ventana Windows física no comprobada. Prueba gráfica Linux: `xvfb-run -a env GC_RENDER_TESTS=1 GC_INTERACT_TESTS=1 PYTHONPATH=src python -m unittest discover -s tests -p test_view.py -v`.
