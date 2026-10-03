# TASK-007: Exponer el colector NVIDIA para Prometheus

| Campo | Valor |
|---|---|
| Status | `done` |
| Owner | — |
| Created | 2026-08-29T12:30:00Z |
| Updated | 2026-08-29T12:50:00Z |
| Depends on | TASK-006 |
| Execution | `orchestrated` |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s / 2048 output / reasoning none |
| Rounds | 3 |
| Contract tests | `monitoring.contract_tests.test_nvidia_textfile_contract` |
| Working directory | Repository root |

## Objetivo

Crear `python3 -m monitoring.nvidia_textfile --directory DIR [--timeout N]`.
Escribe sólo `local_ai_nvidia.prom` mediante temporal y `os.replace`.

## Contrato cerrado

`DIR` debe existir y `N` ser positivo; ambos errores devuelven `2` sin escribir.
Éxito sustituye el fichero y devuelve `0`. Un fallo del colector escribe
exactamente `local_ai_gpu_scrape_success 0\n` y devuelve `3`; no deja temporales.

## Archivos

- `monitoring/nvidia_textfile.py`
