# Hardware
Medido: Debian 13 x86_64, Xeon Platinum 8573C, 5 CPU lógicas visibles, cuota equivalente 4, límite cgroup 4 GiB, GPU no medida, DISPLAY :0 y Xvfb disponibles; no se ejecutó GUI. C++20 probado. Propuesta Windows (no verificada): modesto 4C/8GiB/iGPU 1080p; referencia 8C/16GiB/GPU compatible Qt 1080p; avanzado 16C/32GiB/GPU discreta 1440p. Requisitos reales se establecerán por medición. Windows 10/11 x64 objetivo, CI Windows Server no sustituye ambas pruebas.

GC-PKG-01: destino de experimento Windows Server 2022 x64 en GitHub Actions, Windows 10/11 x64 objetivo; self-test Qt offscreen no verifica WGL/GPU. No hay validación física ni requisitos mínimos finales.

GC-PKG-01: instalación y desinstalación por usuario verificadas en Windows Server 2022 x64 CI, self-test Qt offscreen, sin hardware físico. No equivale validación Windows 10 y 11 ni de OpenGL real.
