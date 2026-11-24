# GC-UI-05 — verificar cierre Qt y recuperación
1. Consultar CI de HEAD; inspeccionar logs Qt completos además de código de salida, confirmar ausencia de RecursionError en cierre/GC y tests de recuperación/cancelación. Windows software Mesa 45506457843 aprobado; GPU real pendiente.
2. Consultar benchmark sync/async 45506930080 y posteriores; registrar datos brutos y latencia. No atribuir mejora sin mediciones comparables.
3. P0 siguiente: carga y guardado físico asíncronos, meshing fuera del hilo GUI sin VTK fuera del dueño, autosave y recuperación segura. Instalador Windows 10/11 real pendiente.
