# Benchmark: desktop-ryzen7-5800x-32gb

- Suite: `quick-v1`
- Ejecución: `20260827T141123Z`
- Backend configurado: `cpu`
- CPU: AMD Ryzen 7 5800X 8-Core Processor
- Memoria: 31.3 GiB
- Acelerador: NVIDIA GeForce RTX 3060, NVIDIA Corporation GA104 [GeForce RTX 3060] (rev a1)
- Inicio: 2026-08-27T14:11:23.829144Z
- Fin: 2026-08-27T14:14:34.632955Z

| Modelo | Perfil | Escenario | Estado | tokens/s | Pico RSS | RAM proceso | Swap proceso | VRAM proceso | AMD VRAM Δ | AMD GTT Δ | GPU AMD máx. | RAM disponible Δ | Swap base | Swap pico | Swap Δ | Compresión Δ | Colocación | Topología | Spill | Presión | CUDA UM | Capas GPU |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---:|
| qwen2.5-1.5b-instruct-q4_k_m | default | pp512 | ok | 274.35 | 1.8 GiB | 1.8 GiB | 0.0 GiB | desconocida | desconocida | desconocida | — | 0.7 GiB | 0.0 GiB | 0.0 GiB | 0.0 GiB | desconocida | cpu | host | none | normal | no | 0 |
| qwen2.5-1.5b-instruct-q4_k_m | default | pp4096 | ok | 226.61 | 1.9 GiB | 1.9 GiB | 0.0 GiB | desconocida | desconocida | desconocida | — | 0.9 GiB | 0.0 GiB | 0.0 GiB | 0.0 GiB | desconocida | cpu | host | none | normal | no | 0 |
| qwen2.5-1.5b-instruct-q4_k_m | default | tg128 | ok | 29.09 | 1.7 GiB | 1.7 GiB | 0.0 GiB | desconocida | desconocida | desconocida | — | 0.6 GiB | 0.0 GiB | 0.0 GiB | 0.0 GiB | desconocida | cpu | host | none | normal | no | 0 |

> Los resultados describen el sistema completo (hardware, sistema operativo, drivers y runtime).
