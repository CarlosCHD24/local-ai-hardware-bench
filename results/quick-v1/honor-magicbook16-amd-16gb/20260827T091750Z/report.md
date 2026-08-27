# Benchmark: honor-magicbook16-amd-16gb

- Suite: `quick-v1`
- Ejecución: `20260827T091750Z`
- Backend configurado: `vulkan`
- CPU: AMD Ryzen 5 4600H with Radeon Graphics
- Memoria: 15.0 GiB
- Acelerador: AMD Unknown (RADV RENOIR) (unified)
- Inicio: 2026-08-27T09:17:50.627005Z
- Fin: 2026-08-27T09:21:52.057806Z

| Modelo | Perfil | Escenario | Estado | tokens/s | Pico RSS | RAM proceso | Swap proceso | VRAM proceso | AMD VRAM Δ | AMD GTT Δ | GPU AMD máx. | RAM disponible Δ | Swap base | Swap pico | Swap Δ | Compresión Δ | Colocación | Topología | Spill | Presión | CUDA UM | Capas GPU |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---:|
| qwen2.5-1.5b-instruct-q4_k_m | default | pp512 | ok | 248.20 | 0.1 GiB | 0.1 GiB | 0.0 GiB | desconocida | 0.1 GiB | 1.3 GiB | 100 % | 1.4 GiB | 0.0 GiB | 0.0 GiB | 0.0 GiB | desconocida | unified_gpu | unified | shared_memory_pressure | normal | no | 99 |
| qwen2.5-1.5b-instruct-q4_k_m | default | pp4096 | ok | 172.46 | 0.1 GiB | 0.1 GiB | 0.0 GiB | desconocida | 0.1 GiB | 1.3 GiB | 100 % | 1.4 GiB | 0.0 GiB | 0.0 GiB | 0.0 GiB | desconocida | unified_gpu | unified | shared_memory_pressure | normal | no | 99 |
| qwen2.5-1.5b-instruct-q4_k_m | default | tg128 | ok | 26.30 | 0.1 GiB | 0.1 GiB | 0.0 GiB | desconocida | 0.1 GiB | 1.0 GiB | 100 % | 1.1 GiB | 0.0 GiB | 0.0 GiB | 0.0 GiB | desconocida | unified_gpu | unified | shared_memory_pressure | normal | no | 99 |

> Los resultados describen el sistema completo (hardware, sistema operativo, drivers y runtime).
