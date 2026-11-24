# GC-UI-03 / GC-UI-02 — validar ventana y software OpenGL
1. Consultar CI del HEAD y runs 45506319546 y 45506319615; corregir fallos reales, especialmente Windows Mesa y pruebas Qt.
2. P0: ejecución asíncrona y cancelación segura de operaciones documentales; medir latencias de confirmación y render, no bloquear UI en cálculos largos.
3. Validar apertura fallida, edición inválida y CAS; registrar métricas y resultados efectivos. Probar ventana nativa Windows 10/11 con GPU real cuando exista entorno.
