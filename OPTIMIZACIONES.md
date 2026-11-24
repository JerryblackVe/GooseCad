# Optimizaciones
O-001: revisar flujo booleano detectó doble BRepCheck_Analyzer del resultado; reutiliza validación interna sin omitir validación de entradas/resultados. Patch results/remove-revalidation.patch (revertir para reproducir baseline). Medianas seriales antes/después ms: union 7.9183/6.7923; cut 5.8748/5.3627; common 5.9358/5.4734. 10/10 pruebas antes y después y validación analítica en 900 muestras. Primitivas no modificadas; variación muestra ruido. No se midió perfil de CPU ni memoria; confirmar en más rondas. Paralelismo de modelos pequeños más lento; queda opt-in.

GC-TOPO-01: índice de pertenencia reutilizado, sin comparación contra implementación lineal; no se afirma aceleración.
