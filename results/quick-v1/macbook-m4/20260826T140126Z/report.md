# Benchmark: macbook-m4

- Suite: `quick-v1`
- Ejecución: `20260826T140126Z`
- Backend configurado: `metal`
- CPU: Apple M4
- Memoria: 16.0 GiB
- Inicio: 2026-08-26T14:01:37.093336Z
- Fin: 2026-08-26T14:07:37.193203Z

| Modelo | Escenario | Estado | tokens/s | Desv. | Pico RSS | Backend | Hilos | Capas GPU |
|---|---|---:|---:|---:|---:|---|---:|---:|
| qwen2.5-1.5b-instruct-q4_k_m | pp512 | ok | 1164.78 | 1.16 | 1.2 GiB | metal | 4 | 99 |
| qwen2.5-1.5b-instruct-q4_k_m | pp4096 | ok | 1022.37 | 22.52 | 1.3 GiB | metal | 4 | 99 |
| qwen2.5-1.5b-instruct-q4_k_m | tg128 | ok | 88.94 | 0.50 | 1.2 GiB | metal | 4 | 99 |
| qwen2.5-3b-instruct-q4_k_m | pp512 | ok | 524.11 | 0.96 | 2.1 GiB | metal | 4 | 99 |
| qwen2.5-3b-instruct-q4_k_m | pp4096 | ok | 478.25 | 0.12 | 2.2 GiB | metal | 4 | 99 |
| qwen2.5-3b-instruct-q4_k_m | tg128 | ok | 47.55 | 0.07 | 2.1 GiB | metal | 4 | 99 |
| qwen2.5-7b-instruct-q4_k_m | pp512 | ok | 231.70 | 0.25 | 4.5 GiB | metal | 4 | 99 |
| qwen2.5-7b-instruct-q4_k_m | pp4096 | ok | 219.19 | 0.03 | 4.7 GiB | metal | 4 | 99 |
| qwen2.5-7b-instruct-q4_k_m | tg128 | ok | 22.04 | 0.06 | 4.5 GiB | metal | 4 | 99 |

> Los resultados describen el sistema completo (hardware, sistema operativo, drivers y runtime).
