# Revisión GC-MESH-01 (afad1c07f827b899cc9e1fc688a1c0b9f3036632)
Correcciones sobre HEAD posterior a MESH-02 y VIEW-01, sin revertir historial.

## 1. Espejo
Prueba de reflexión planar gp_Trsf.SetMirror sobre caja y esfera desplazadas. Se cubren ubicación negativa y copia BRepBuilderAPI_Transform; OCCT devuelve masa firmada negativa para la ubicación negativa directa, pero la malla corregida tiene volumen positivo. La copia reflejada válida tiene masa B-Rep positiva analítica. La esfera produce dos triángulos de área cero en polos; se exige orientación exterior en todos los no degenerados y error relativo de volumen menor a 0,5%. Arrays y offsets iguales entre las dos rutas. Primera prueba falló por normales nulas, corregido el criterio sin excluir normales invertidas no degeneradas. 157/157 pruebas con Xvfb, sin skips.
