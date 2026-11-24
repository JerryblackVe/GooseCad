# Sincronización
2026-11-24: acceso GitHub con conector, pull/push/admin declarados. main e6857e19bbc89ed9b910ea3a900a950b962d9ce7; develop 93e647632a58f76df8d05e5919fe472e9ec0d3e8. Ambas no protegidas según listado; rulesets vacío. develop contiene .github, LICENSE, requirements.txt, src y tests; no se importaron. main README. No cambios remotos, ni escritura ensayada: público, se requiere confirmación. CI histórico no aplica. Rama local feature/000-clean-start; checkpoint nuevo NO SINCRONIZADO; recuperar ZIP/bundle y reconciliar con main sin force push.

2026-11-24: publicación expresamente autorizada con exclusión de medios y datos privados. Git terminal sigue bloqueado por DNS. Transferencia por API en rama nueva basada en main; SHA final se verifica externamente.

GC-BOOT: API GitHub, rama feature/000-clean-start, SHA 8225a910d044aa2b3c9bb0bf460230b9641063ff; 55/55 hashes verificados. main/develop preservadas.

GC-TOPO-01: 0bb0b9b55993e4f69ee4797f7ecfac491f6e47d0; 60/60 hashes verificados, CI Windows/Linux aprobado run 45485337287. GC-TOPO-02 se publica mediante API no forzada; SHA final externo.

GC-TOPO-02: d80bc6ea54b206391e6d31d6d0781152af481237, árbol 416ba1a202babf240961360b79ba0bbe135499f9, 66 archivos. CI Windows/Linux aprobado run 45487040637. GC-DAG-01 se publica mediante API sin force, SHA final externo; CI nuevo pendiente de verificación.

GC-DAG-01: a07254830d74cb779b2ffde91636b50cd13c770b, árbol c1dad6b4b97d71cccbf477e37dd97b52a3cdcb35, 75 archivos verificados. CI run 45488199339 en ejecución al consultar. GC-DOC-01 se publica por API no forzada; SHA final externo.

GC-DOC-02: base remota 374461bc3624325cabcf6d6ad40ad2b5d7326a73 verificada; CI DOC-01 ambos jobs aprobados (45488649604); nuevo SHA reportado tras verificación externa.

GC-SOLVER-01: base remota 06bc3ba9f2ef6e6180e8e23312e1cdbd0f9a3416 y árbol 4cf89288bcffb4e16d54a76e78f5ca8a08c1fc3f verificados; nuevo SHA reportado tras verificación externa.

GC-ABI-01 base remota 4bd459e9ec7908fe7acba984710c2e831f702ee2; publicación vía API sin force; SHA final externo; verificar CI.
