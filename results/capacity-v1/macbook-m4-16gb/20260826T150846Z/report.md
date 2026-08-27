# Benchmark: macbook-m4-16gb

- Suite: `capacity-v1`
- Ejecución: `20260826T150846Z`
- Backend configurado: `metal`
- CPU: Apple M4
- Memoria: 16.0 GiB
- Inicio: 2026-08-26T15:08:47.102228Z
- Fin: 2026-08-26T15:10:04.960634Z

| Modelo | Perfil | Escenario | Estado | tokens/s | Pico RSS | Swap base | Swap pico | Swap Δ | Compresión Δ | Colocación | Presión | Capas GPU |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---:|
| qwen2.5-14b-instruct-q4_k_m | auto-fit | tg32 | ok | 11.35 | 5.9 GiB | 0.0 GiB | 2.3 GiB | 2.3 GiB | 1.8 GiB | unified_gpu | swapping | 49 |
| qwen2.5-14b-instruct-q4_k_m | auto-fit | pp512 | ok | 120.38 | 8.5 GiB | 2.3 GiB | 2.4 GiB | 0.1 GiB | 0.0 GiB | unified_gpu | swapping | 49 |
| qwen2.5-14b-instruct-q4_k_m | full-accelerator | tg32 | ok | 11.54 | 8.5 GiB | 2.4 GiB | 2.4 GiB | 0.0 GiB | 0.0 GiB | unified_gpu | normal | 49 |
| qwen2.5-14b-instruct-q4_k_m | full-accelerator | pp512 | ok | 117.85 | 8.5 GiB | 2.4 GiB | 2.4 GiB | 0.0 GiB | 0.3 GiB | unified_gpu | compressed | 49 |

> Los resultados describen el sistema completo (hardware, sistema operativo, drivers y runtime).
