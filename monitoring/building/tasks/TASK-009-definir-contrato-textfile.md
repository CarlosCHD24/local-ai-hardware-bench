# TASK-009: Validar la configuración de Prometheus

| Campo | Valor |
|---|---|
| Status | `done` |
| Owner | — |
| Created | 2026-08-29T12:42:00Z |
| Updated | 2026-08-29T12:50:00Z |
| Depends on | TASK-008 |
| Execution | `orchestrated` |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s / 2048 output / reasoning none |
| Rounds | 3 |
| Contract tests | `monitoring.contract_tests.test_prometheus_files_contract` |
| Working directory | Repository root |

## Objetivo

Crear `python3 -m monitoring.validate_prometheus --config PATH`. Devuelve `0`
sólo con los dos jobs locales, intervalo de 15 s, `/metrics` y
`bearer_token_file` sin secreto literal; `1` para contenido inválido y `2` para
argumentos o fichero inexistente.

## Archivos

- `monitoring/validate_prometheus.py`
