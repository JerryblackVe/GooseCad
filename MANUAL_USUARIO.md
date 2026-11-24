# Uso experimental
No hay aplicación de escritorio. Para ingeniería: importar box, cylinder, sphere, boolean, properties desde goosecad.geometry.kernel. Ejemplo `properties(box(10,20,30))` devuelve volumen 6000 mm³. Booleanos: union/cut/common; no editar objetos nativos compartidos. Ver pruebas para ejemplos. Manual gráfico, 12 temas y modos pendientes.

GC-SKETCH-02: documentos v1/v2, bocetos poligonales declarativos y barridos B-Rep; consultar docs/FORMATO_NATIVO.md. CI previo Windows/Linux aprobado; nuevo CI pendiente. No es aplicación de escritorio.

GC-DOC-03: guardado con bloqueo cooperativo y token de revisión de disco; ver docs/FORMATO_NATIVO.md. Pruebas locales aprobadas; verificar CI Windows/Linux.


GC-SKETCH-03: creación de regiones curvas por API, ver docs/FORMATO_NATIVO.md. Todavía sin interfaz.


GC-MESH-01: tessellate(shape, linear=.1, angular=.5) devuelve datos de visualización. No es visor interactivo.


GC-MESH-02: caché LRU por instancia de documento, cuerpo, revisión de nodo y configuración completa. DAG publica sello junto al valor en la misma transacción. 151 pruebas locales (9 nuevas), 120 muestras de caché y 400 de regresión DAG (8790 acumuladas). 20 esferas: reconstrucción 118.6522 ms, edición de una 6.4281 ms, caliente 0.02764 ms; buffers equivalentes exactos entre caché y directo, ~492752 bytes contabilizados en última muestra. No es FPS. Presupuesto por buffers y offsets más límite de entradas; excluye overhead completo, memoria OCCT/GPU y referencias externas. Snapshots prestados de solo lectura (incluida metadata NumPy), bytes inmutables, comprobar is_current antes de presentar/seleccionar. Reload/recovery crea nueva caché. Misses simultáneos pueden duplicar trabajo; no se garantiza ejecución concurrente OCCT, snapshots viejos no son hits actuales. No hay persistencia de mallas ni selección topológica persistente.


GC-VIEW-01 (experimental): `python -m goosecad.view` abre el ejemplo de caja; `python -m goosecad.view archivo.gcad id_cuerpo [id_cuerpo2 ...]` abre un documento existente de confianza en modo solo visualización. Ratón trackball, R ajustar cámara, P seleccionar bajo cursor (ID de cara local impreso en terminal, resalta cuerpo), Q salir. VTK 9.6.2 ya incluido en requirements-core. Linux Xvfb/EGL comprobados; ventana Windows física no comprobada. Prueba gráfica Linux: `xvfb-run -a env GC_RENDER_TESTS=1 GC_INTERACT_TESTS=1 PYTHONPATH=src python -m unittest discover -s tests -p test_view.py -v`.

## Ventana de documentos experimental
Abrir un documento nativo .gcad/.goosecad o iniciar la caja de ejemplo; modificar celdas de valor y pulsar Aplicar cambios. Deshacer/Rehacer operan sobre los parámetros; no hay cambios estructurales ni historial persistido. Guardar conserva la revisión de disco; conflicto externo rechaza guardado. Guardar como solo crea archivo nuevo. Vista: trackball, ajustar vista y tecla P sobre el cuerpo para seleccionar cara local. Cancelar cálculo solicita cancelación en punto seguro; no interrumpe una llamada OCCT en curso. El cierre ocupado se rechaza. Esta edición aún no es estable y no está validada en Windows físico.

Recuperar versión anterior: menú Archivo → Recuperar versión anterior, seleccionar el archivo principal. Se abre su .previous como documento sin nombre con cambios sin guardar. Guardar como requiere una ruta nueva y nunca reemplaza el original. Si la versión anterior no existe o está dañada, se conserva el documento actual.
