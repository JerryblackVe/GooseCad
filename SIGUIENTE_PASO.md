# GC-UI-04 P0 — integrar trabajo asíncrono en Qt
1. Consultar CI de HEAD; GC-UI-03 45506319546 y Mesa 45506457843, revisar resultados gráficos y mediciones. Corregir errores reproducibles.
2. Integrar DocumentTasks en MainWindow: un QTimer recoge resultados, controles/documento/visor no se consultan durante worker, cancelación cooperativa y cierre seguro. Mantener edición por lote y protección CAS. Añadir pruebas Qt de éxito, cancelación y cierre.
3. Medir latencia de respuesta y cálculo por separado. Validación Windows 10/11 real, instalador y resto de alcance pendientes.
