# TASK-005: Crear colector de métricas NVIDIA

| Campo | Valor |
|---|---|
| Status | `ready` |
| Owner | — |
| Created | 2026-08-28T22:52:58Z |
| Updated | 2026-08-28T22:52:58Z |
| Depends on | TASK-004 |
| Execution | `orchestrated` |
| Execution manifest | Obligatorio por job |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s / 2048 output / reasoning none |
| Rounds | 3 |
| Contract tests | `monitoring.contract_tests.test_nvidia_metrics_contract` |
| Working directory | Raíz exacta indicada en el manifiesto |

## Objetivo

Crear un comando Python que ejecute `nvidia-smi` una vez y emita métricas
Prometheus deterministas, sin dependencias externas.

## Contrato cerrado

Comando:

```text
python3 -m monitoring.nvidia_metrics [--timeout 5]
```

Ejecutar con `subprocess.run`, sin shell y con timeout:

```text
nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,power.limit --format=csv,noheader,nounits
```

Aceptar varias filas CSV, ordenar por índice, convertir porcentajes a ratio y
MiB a bytes. Emitir `# HELP`, `# TYPE` y estas gauges con etiqueta `gpu`:

```text
local_ai_gpu_utilization_ratio
local_ai_gpu_memory_used_bytes
local_ai_gpu_memory_total_bytes
local_ai_gpu_temperature_celsius
local_ai_gpu_power_watts
local_ai_gpu_power_limit_watts
local_ai_gpu_scrape_success
```

En éxito, código `0` y success `1` por GPU. Timeout `<= 0` devuelve `2` sin
subprocess. Binario ausente, timeout, código no cero, CSV incompleto, `N/A` o
número inválido devuelve `3`, error fijo sin salida externa y únicamente
`local_ai_gpu_scrape_success 0` en stdout.

`nvidia-smi` no existe en Honor: todas las pruebas simulan `subprocess.run` y el
smoke test real queda fuera de esta tarea.

## Preflight

| Directorio | Comando exacto | Código esperado |
|---|---|---:|
| Raíz | `python3 -c "import csv, subprocess, unittest"` | `0` |
| Raíz | `python3 -m py_compile monitoring/contract_tests/test_nvidia_metrics_contract.py` | `0` |
| Raíz | `python3 -m unittest discover -s monitoring/tests -p 'test_*.py'` | `0` |

## Archivos permitidos

- `monitoring/nvidia_metrics.py`

No crear tests adicionales ni modificar los tests de contrato.

## Verificación obligatoria

| Directorio | Comando exacto | Código esperado |
|---|---|---:|
| Raíz | `python3 -m unittest monitoring.contract_tests.test_nvidia_metrics_contract` | `0` |
| Raíz | `python3 -m unittest discover -s monitoring/tests -p 'test_*.py'` | `0` |
| Raíz | `python3 -m monitoring.nvidia_metrics --help` | `0` |
| Raíz | `git diff --check` | `0` |

## Resultado

Entregar el formato de `HERMES_TASK_GUIDE.md`. No buscar GPU en otros hosts.

## Handoff

Sin trabajo pendiente ni bloqueos.
