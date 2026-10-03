# TASK-013: Provisionar la fuente de datos Grafana

| Campo | Valor |
|---|---|
| Status | `done` |
| Owner | — |
| Created | 2026-08-29T13:00:00Z |
| Updated | 2026-08-29T13:00:00Z |
| Depends on | TASK-008 |
| Execution | `orchestrated` |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s |
| Rounds | 3 |
| Contract tests | comprobación estática del YAML |
| Working directory | Repository root |

## Objetivo

Crear provisioning de Grafana que use Prometheus en `http://127.0.0.1:9090`,
con acceso por defecto y sin credenciales en Git.

## Archivos

- `monitoring/grafana/provisioning/datasources/prometheus.yml`
