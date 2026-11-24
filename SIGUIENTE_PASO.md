# GC-UI-06 — verificar archivos asíncronos y reducir latencia de publicación
Consultar CI de HEAD y GC-UI-05; revisar logs de cierre (no solo exit code). Validar pruebas de archivos asíncronos. P0: sustituir polling fijo Qt por señal de finalización en hilo GUI, medir retorno y fin total en mismo runner. Después separar teselación y guardado automático seguro.
