# Benchmark: desktop-rtx3060-12gb

- Suite: `quick-v1`
- Ejecución: `20260827T143915Z`
- Backend configurado: `cuda`
- CPU: AMD Ryzen 7 5800X 8-Core Processor
- Memoria: 31.3 GiB
- Acelerador: NVIDIA GeForce RTX 3060, NVIDIA Corporation GA104 [GeForce RTX 3060] (rev a1)
- Inicio: 2026-08-27T14:39:15.399628Z
- Fin: 2026-08-27T14:40:23.713747Z

| Modelo | Perfil | Escenario | Estado | tokens/s | Pico RSS | RAM proceso | Swap proceso | VRAM proceso | AMD VRAM Δ | AMD GTT Δ | GPU AMD máx. | RAM disponible Δ | Swap base | Swap pico | Swap Δ | Compresión Δ | Colocación | Topología | Spill | Presión | CUDA UM | Capas GPU |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---:|
| qwen2.5-1.5b-instruct-q4_k_m | default | pp512 | ok | 8085.88 | 1.3 GiB | 0.0 GiB | 0.0 GiB | desconocida | desconocida | desconocida | — | 0.1 GiB | 0.0 GiB | 0.0 GiB | 0.0 GiB | desconocida | gpu_full | dedicated | none | normal | no | 99 |
| qwen2.5-1.5b-instruct-q4_k_m | default | pp4096 | ok | 7717.04 | 1.3 GiB | 0.4 GiB | 0.0 GiB | 1.4 GiB | desconocida | desconocida | — | 0.1 GiB | 0.0 GiB | 0.0 GiB | 0.0 GiB | desconocida | gpu_full | dedicated | none | normal | no | 99 |
| qwen2.5-1.5b-instruct-q4_k_m | default | tg128 | ok | 209.56 | 1.3 GiB | 0.4 GiB | 0.0 GiB | 1.1 GiB | desconocida | desconocida | — | 0.1 GiB | 0.0 GiB | 0.0 GiB | 0.0 GiB | desconocida | gpu_full | dedicated | none | normal | no | 99 |
| qwen2.5-3b-instruct-q4_k_m | default | pp512 | ok | 4372.66 | 2.2 GiB | 0.5 GiB | 0.0 GiB | 2.2 GiB | desconocida | desconocida | — | 0.1 GiB | 0.0 GiB | 0.0 GiB | 0.0 GiB | desconocida | gpu_full | dedicated | none | normal | no | 99 |
| qwen2.5-3b-instruct-q4_k_m | default | pp4096 | ok | 4199.74 | 2.2 GiB | 0.5 GiB | 0.0 GiB | 2.3 GiB | desconocida | desconocida | — | 0.2 GiB | 0.0 GiB | 0.0 GiB | 0.0 GiB | desconocida | gpu_full | dedicated | none | normal | no | 99 |
| qwen2.5-3b-instruct-q4_k_m | default | tg128 | ok | 131.85 | 2.2 GiB | 0.4 GiB | 0.0 GiB | 2.0 GiB | desconocida | desconocida | — | 0.1 GiB | 0.0 GiB | 0.0 GiB | 0.0 GiB | desconocida | gpu_full | dedicated | none | normal | no | 99 |
| qwen2.5-7b-instruct-q4_k_m | default | pp512 | ok | 2345.52 | 4.6 GiB | 0.6 GiB | 0.0 GiB | 4.5 GiB | desconocida | desconocida | — | 0.2 GiB | 0.0 GiB | 0.0 GiB | 0.0 GiB | desconocida | gpu_full | dedicated | none | normal | no | 99 |
| qwen2.5-7b-instruct-q4_k_m | default | pp4096 | ok | 2219.82 | 4.6 GiB | 0.6 GiB | 0.0 GiB | 4.7 GiB | desconocida | desconocida | — | 0.1 GiB | 0.0 GiB | 0.0 GiB | 0.0 GiB | desconocida | gpu_full | dedicated | none | normal | no | 99 |
| qwen2.5-7b-instruct-q4_k_m | default | tg128 | ok | 68.41 | 4.6 GiB | 0.6 GiB | 0.0 GiB | 4.3 GiB | desconocida | desconocida | — | 0.2 GiB | 0.0 GiB | 0.0 GiB | 0.0 GiB | desconocida | gpu_full | dedicated | none | normal | no | 99 |

> Los resultados describen el sistema completo (hardware, sistema operativo, drivers y runtime).
