# Formato GooseCAD v1/v2 experimental

JSON canónico UTF-8, checksum SHA-256 del objeto format/version/payload; detecta corrupción accidental, no autentica. Unidades mm y radianes. Los archivos v1 conservan su esquema y versión. v2 añade `sketches` (lista) al payload; cada boceto tiene `id`, `points` (lista ordenada de `{id,x,y}`, x/y son IDs de parámetros numéricos), `constraints` (lista de `{id,kind,a,b,targets}`). IDs de puntos/restricciones son únicos dentro del boceto. `fix` usa b=null y dos IDs de parámetros; `distance` usa dos puntos y un ID de parámetro; `horizontal`, `vertical`, `coincident` usan dos puntos y targets vacío. El perfil usa todos los puntos en orden y se cierra automáticamente. `extrude` y `revolve` son features v2 con dependencias `[sketch_id,parameter_id]`; ambas retornan sólidos B-Rep. El esquema anterior de operaciones se conserva.

Crear con `NativeDocument(params, features, sketches=[SketchSpec(...)])`; tipos PointSpec/ConstraintSpec/SketchSpec disponibles en `goosecad.document.native`. Los cambios de parámetros mediante edit/undo/redo reconstruyen solo descendientes. Las semillas y cotas se guardan, no las formas ni historial. `load`, `save`, `recover` comparten protección atómica existente. Abrir v1 no lo convierte; `upgraded()` crea documento independiente v2 sin historial. Para reemplazar un archivo v1 con v2 se necesita `save(new_doc,path,allow_upgrade=True)`; conserva el v1 en `.previous` hasta el próximo guardado. Preferir guardar en otro nombre para preservar v1 indefinidamente. Downgrade rechazado. No editar archivos directamente; validación de esquema previa a evaluación no es sandbox de OCCT. El protocolo de bloqueo cooperativo GC-DOC-03 se detalla a continuación. Límites y pendientes en ESTADO_PROYECTO.md.

## Control de escritores y revisiones

```python
from goosecad.document.native import load_with_revision, save
model, revision = load_with_revision(path)
model.edit({"height": 5})
revision = save(model, path, expected_revision=revision)
```

Para un archivo nuevo, `expected_revision=None` exige que no exista. Un token de bytes exactos rechaza un guardado obsoleto antes de crear o alterar `.previous`. Si se omite el token se conserva la semántica previa: reemplazo incondicional de un archivo estructuralmente válido. Para futuras interfaces, siempre usar el token. `WriterBusyError` indica lock existente, `DiskRevisionConflict` indica conflicto de bytes/ausencia. No reintentar ciegamente. Guardar como otro nombre si se quiere conservar ambas versiones.

El sidecar `<nombre>.goosecad-lock` es reservado, creado con exclusividad; no se elimina un lock existente ni se roba por antigüedad. Si hubo terminación abrupta, comprobar que todos los escritores se han cerrado, preservar el archivo principal y `.previous`, y solo entonces retirar manualmente el sidecar. Abrir la versión de recuperación nunca sobrescribe el principal. Tras fallo posterior al reemplazo, releer y obtener token antes de otro guardado. Protocolo cooperativo para directorios locales confiables; no sandbox, autenticación, protección frente a aplicaciones que ignoran el lock ni garantía en red o corte de corriente.
