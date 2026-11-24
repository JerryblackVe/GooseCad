# Dependencias
CPython 3.13.5, cadquery-ocp 7.9.3.1.1 (OCP 7.9.3.1), VTK 9.6.2 y transitivas fijadas desde entorno real Linux en dependencies/requirements-core.txt. El lock no incluye hashes ni build backend transitivo y no está validado en Windows. No se incluye binario de terceros. GCC 14.2.0, CMake 3.31.6, Git 2.47.3 y Ninja detectados. Goose, C++ OCCT SDK, Qt/PySide, FreeCAD, SolveSpace, Eigen, OpenGL/Vulkan, instaladores y otras dependencias futuras no adoptados. Auditoría de versiones/licencias antes de distribución. Ver docs/FUENTES.md.

GC-SOLVER-01 añade dependencia SciPy 1.17.0; NumPy 2.3.5 (ya en lock) ahora explícita en pyproject.toml. Versiones instaladas y pruebas Linux reales; CI Windows pendiente.


GC-ABI-01: prueba C/C++ escalar independiente, ABI v1, IDs monotónicos, registro acotado, propiedad explícita create/release, errores enteros y noexcept, consulta por lote validada antes de escribir. GCC/CMake Release y ASan/UBSan con CTest aprobados; 10.000 ciclos de vida; 78 pruebas Python aprobadas. 200 muestras ctypes (256 consultas, mediana escalar 0.1373635 ms, lote 0.002274 ms). No incluye Goose ni OCCT; no es benchmark del kernel. Goose no instalado, SDK C++ OCCT ausente, DNS bloqueado. Buffers válidos/no solapados a cargo del llamador, IDs locales al proceso/biblioteca, mutex global, no se ha probado concurrencia ni FFI Goose. CI CMake Windows/Linux preparado, aún no ejecutado para este commit. Siguiente GC-GEO-02: perfiles de boceto resueltos, extrusión/revolución B-Rep.

GC-VIEW-01: VTK 9.6.2 (ya fijado en requirements-core) se utiliza directamente para visor. Qt no instalado; no nueva dependencia instalada.

GC-UI-02: PySide6 6.11.3 evaluado como candidato, NO instalado ni fijado en las dependencias del programa. Existe rueda Python 3.13 Windows x64 (abi3); antes de incorporar comprobar dependencias Qt completas, compatibilidad de VTK 9.6.2, licencias y redistribución. Fuente: https://pypi.org/project/PySide6/6.11.3/

Mesa Windows CI experimental: pal1000/mesa-dist-win 25.3.5 release-msvc, x64; upstream asset SHA256 066f64549ac122bfad4d68c2c4ec9b0018d025a1af7fa61654d3ccbc5e933388. CI-only (no application distribution), no system-wide deployment. Fuentes: https://github.com/pal1000/mesa-dist-win/releases/tag/25.3.5 y https://docs.vtk.org/en/latest/advanced/runtime_settings.html .
