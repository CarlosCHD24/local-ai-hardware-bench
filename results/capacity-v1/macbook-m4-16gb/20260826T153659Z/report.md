# Benchmark: macbook-m4-16gb

- Suite: `capacity-v1`
- Ejecución: `20260826T153659Z`
- Backend configurado: `metal`
- CPU: Apple M4
- Memoria: 16.0 GiB
- Inicio: 2026-08-26T15:36:59.609093Z
- Fin: 2026-08-26T15:38:08.879548Z

| Modelo | Perfil | Escenario | Estado | tokens/s | Pico RSS | Swap base | Swap pico | Swap Δ | Compresión Δ | Colocación | Presión | Capas GPU |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---:|
| qwen2.5-32b-instruct-q4_k_m | auto-fit | tg32 | aborted_pressure | — | desconocida | 2.4 GiB | 11.0 GiB | 8.6 GiB | 1.6 GiB | unknown | aborted | — |
| qwen2.5-32b-instruct-q4_k_m | auto-fit | pp512 | skipped | — | desconocida | desconocida | desconocida | desconocida | desconocida | — | — | — |

## Incidencias

- `qwen2.5-32b-instruct-q4_k_m / auto-fit / tg32`: ed_reserve: reserving ... sched_reserve: max_nodes = 6168 sched_reserve: reserving full memory module sched_reserve: worst-case: n_tokens = 32, n_seqs = 1, n_outputs = 1 graph_reserve: reserving a graph for ubatch with n_tokens =    1, n_seqs =  1, n_outputs =    1 resolve_fused_ops: Flash Attention enabled resolve_fused_ops: resolving fused Gated Delta Net support: graph_reserve: reserving a graph for ubatch with n_tokens =    1, n_seqs =  1, n_outputs =    1 resolve_fused_ops: fused Gated Delta Net (autoregressive) enabled graph_reserve: reserving a graph for ubatch with n_tokens =   16, n_seqs =  1, n_outputs =   16 resolve_fused_ops: fused Gated Delta Net (chunked) enabled resolve_fused_ops: resolving fused Lightning Indexer support: graph_reserve: reserving a graph for ubatch with n_tokens =    1, n_seqs =  1, n_outputs =    1 resolve_fused_ops: Lightning Indexer enabled resolve_fused_ops: resolving fused DeepSeek V4 HC support: graph_reserve: reserving a graph for ubatch with n_tokens =    1, n_seqs =  1, n_outputs =    1 resolve_fused_ops: fused DeepSeek V4 HC pre enabled graph_reserve: reserving a graph for ubatch with n_tokens =    1, n_seqs =  1, n_outputs =    1 resolve_fused_ops: fused DeepSeek V4 HC comb enabled graph_reserve: reserving a graph for ubatch with n_tokens =    1, n_seqs =  1, n_outputs =    1 resolve_fused_ops: fused DeepSeek V4 HC post enabled graph_reserve: reserving a graph for ubatch with n_tokens =   32, n_seqs =  1, n_outputs =   32 graph_reserve: reserving a graph for ubatch with n_tokens =    1, n_seqs =  1, n_outputs =    1 graph_reserve: reserving a graph for ubatch with n_tokens =   32, n_seqs =  1, n_outputs =   32 sched_reserve:       MTL0 compute buffer size =    25.83 MiB sched_reserve:        CPU compute buffer size =    12.64 MiB sched_reserve: graph nodes  = 2182 sched_reserve: graph splits = 2 sched_reserve: reserve took 105.34 ms, sched copies = 1 attach_threadpool: call set_n_threads: n_threads = 4, n_threads_batch = 4
- `qwen2.5-32b-instruct-q4_k_m / auto-fit / pp512`: Omitida tras fallo de memoria

> Los resultados describen el sistema completo (hardware, sistema operativo, drivers y runtime).
