# Revisión GC-MESH-01 (afad1c07f827b899cc9e1fc688a1c0b9f3036632)
Correcciones sobre HEAD posterior a MESH-02 y VIEW-01, sin revertir historial.

## 1. Espejo
Prueba de reflexión planar gp_Trsf.SetMirror sobre caja y esfera desplazadas. Se cubren ubicación negativa y copia BRepBuilderAPI_Transform; OCCT devuelve masa firmada negativa para la ubicación negativa directa, pero la malla corregida tiene volumen positivo. La copia reflejada válida tiene masa B-Rep positiva analítica. La esfera produce dos triángulos de área cero en polos; se exige orientación exterior en todos los no degenerados y error relativo de volumen menor a 0,5%. Arrays y offsets iguales entre las dos rutas. Primera prueba falló por normales nulas, corregido el criterio sin excluir normales invertidas no degeneradas. 157/157 pruebas con Xvfb, sin skips.

## 2. Perfilado y vectorización
cProfile explícito sobre afad1c0 registra 19.760 llamadas de cada min/max/len, pero no atribuye todo el tiempo nativo/Python (ver results/mesh-review-profile.log); cronómetro por etapa complementario. La construcción OCCT domina, la extracción es el segundo coste. OCP no ofrece vista NumPy de Poly_Triangulation; se mantienen accesos nativos por punto/triángulo y transformación gp_Pnt.Transformed exacta. Se vectorizan validación y ajuste de índices, se asignan coordenadas por bloques de 8192; caras con menos de 64 triángulos mantienen ruta escalar. _identity_fast queda como control privado de diagnóstico de igualdad y la decisión se toma por cara, fuera de los bucles, evitando transformaciones nativas inútiles. No se afirma ganancia >10% de esa opción. Comparación intercalada, 30 muestras, 3 warmups, .05 mm/.3 rad, un hilo BLAS, resultados exactos incluyendo espejos y rotación.

| Caso | Ruta | Mediana ms | P95 ms |
|---|---|---:|---:|
| box | baseline | 1.2005 | 1.5299 |
| box | optimized | 1.2193 | 1.4369 |
| box | optimized_transform | 1.1819 | 1.6558 |
| sphere | baseline | 5.8072 | 6.8648 |
| sphere | optimized | 5.1472 | 5.7922 |
| sphere | optimized_transform | 5.4424 | 5.9574 |
| 20_spheres | baseline | 108.7732 | 118.4344 |
| 20_spheres | optimized | 94.1325 | 102.5419 |
| 20_spheres | optimized_transform | 98.7261 | 102.9261 |
| mirror | baseline | 6.3077 | 7.2880 |
| mirror | optimized | 5.4906 | 6.0144 |
| mirror | optimized_transform | 5.4800 | 5.7858 |
| rotation | baseline | 6.1456 | 7.0083 |
| rotation | optimized | 5.4712 | 6.0715 |
| rotation | optimized_transform | 5.6081 | 6.1371 |

157/157 pruebas locales con Xvfb. Reproducir: `PYTHONPATH=src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python benchmarks/mesh_review_bench.py mesh-review.csv --profile mesh-profile.log --baseline afad1c07f827b899cc9e1fc688a1c0b9f3036632 --repetitions 30` (en clon remoto; en copia local se usó 516e9b1 con mismo árbol). Comparación final 450 muestras, sin contar perfil instrumentado.
