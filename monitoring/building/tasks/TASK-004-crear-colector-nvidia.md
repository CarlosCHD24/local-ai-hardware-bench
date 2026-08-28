# TASK-004: Crear colector de métricas NVIDIA

| Campo | Valor |
|---|---|
| Status | `ready` |
| Owner | — |
| Created | 2026-08-28T21:41:16Z |
| Updated | 2026-08-28T21:41:16Z |
| Depends on | TASK-003 |
| Execution | `orchestrated` |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s / 2048 output / reasoning none |
| Working directory | Repository root |

## Objetivo

Crear un comando Python que ejecute `nvidia-smi` una vez y escriba métricas
Prometheus estables en stdout, sin dependencias externas.

## Contexto mínimo

- Leer `monitoring/AGENTS.md`, `building/README.md`,
  `building/HERMES_TASK_GUIDE.md` y esta tarea.
- `nvidia-smi` no existe en Honor; los tests deben simular `subprocess.run`.
- El smoke test real pertenece al auditor en el servidor con GPU.

## Contrato cerrado

Comando:

```text
python3 -m monitoring.nvidia_metrics [--timeout 5]
```

Ejecutar exactamente:

```text
nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,power.limit --format=csv,noheader,nounits
```

Usar `subprocess.run` sin shell, con timeout. Aceptar una o varias filas CSV y
ordenarlas por índice. Convertir porcentajes a ratio y MiB a bytes.

Métricas gauge exactas, todas con etiqueta `gpu` y sin nombre ni UUID:

```text
local_ai_gpu_utilization_ratio
local_ai_gpu_memory_used_bytes
local_ai_gpu_memory_total_bytes
local_ai_gpu_temperature_celsius
local_ai_gpu_power_watts
local_ai_gpu_power_limit_watts
local_ai_gpu_scrape_success
```

Emitir líneas `# HELP` y `# TYPE` deterministas. En éxito, código `0` y
`scrape_success 1` por GPU. Timeout `<= 0` devuelve `2`. Binario ausente,
timeout, código no cero, fila incompleta, valor `N/A` o número inválido devuelve
`3`, escribe error fijo en stderr y únicamente `local_ai_gpu_scrape_success 0`
sin etiqueta en stdout. No incluir la salida original de `nvidia-smi` en el
error.

## Matriz mínima de pruebas

| Prueba | Demuestra |
|---|---|
| Una GPU válida | Valores, tipos y conversiones exactas; código `0` |
| Varias GPU desordenadas | Salida ordenada por índice |
| Timeout no positivo | Código `2`; no ejecuta subprocess |
| Binario ausente o timeout | Código `3` y success `0` |
| Proceso no cero | Código `3` sin copiar stderr externo |
| CSV incompleto, `N/A` o inválido | Código `3` sin salida parcial |
| Invocación | Lista de argumentos exacta, `shell=False` y timeout propagado |

Usar `unittest.mock`, capturar stdout y stderr de la misma invocación y no
cambiar `sys.path`.

## Preflight

| Directorio | Comando exacto | Código esperado |
|---|---|---:|
| Raíz | `python3 -c "import csv, subprocess, unittest"` | `0` |
| Raíz | `python3 -m unittest discover -s monitoring/tests -p 'test_*.py'` | `0` |

## Archivos permitidos

- `monitoring/nvidia_metrics.py`
- `monitoring/tests/test_nvidia_metrics.py`

Antes de `git diff --check`, ejecutar:

```text
git add -N -- monitoring/nvidia_metrics.py monitoring/tests/test_nvidia_metrics.py
```

## Verificación obligatoria

| Directorio | Comando exacto | Código esperado |
|---|---|---:|
| Raíz | `python3 -m unittest discover -s monitoring/tests -p 'test_*.py'` | `0` |
| Raíz | `python3 -m monitoring.nvidia_metrics --help` | `0` |
| Raíz | `git diff --check` | `0` |
| Raíz | `git status --short` | `0`; sólo archivos permitidos y estado del orquestador |

## Resultado

Entregar el formato de `HERMES_TASK_GUIDE.md`. No buscar `nvidia-smi` en otros
hosts y no realizar el smoke test real.
