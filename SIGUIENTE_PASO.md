# GC-UI-02 — Ventana Qt/VTK de escritorio (P1)
1. Verificar resultado de CI de GC-UI-01, run 45502896110 (y commits posteriores), en Windows 2022 y Ubuntu 24.04; corregir fallos.
2. Evaluar PySide6 6.11.3 como candidato NO fijado, junto con una versión Qt anterior a 6.10 por riesgo conocido de integración con VTK, usando `QVTKRenderWindowInteractor`. Registrar compatibilidad real, requisitos LGPL/comercial y licencias de redistribución antes de fijar dependencias.
3. Implementar una ventana de escritorio nativa mínima vinculada a DocumentSession y el visor VTK: abrir, guardar con token, edición de parámetros, deshacer/rehacer, lista/selección de cuerpos, mensajes claros de conflicto y estado dirty. Deshabilitar toda función aún no implementada.
4. Agregar pruebas UI de pérdida de cambios, foco, cierre, render, selección obsoleta, error de disco, controles de teclado y benchmark reproducible de interacción. Ejecutar CI Windows y Linux.
5. No proclamar paridad con Fusion, accesibilidad completa, FPS GPU ni instalador hasta verificarlos.
