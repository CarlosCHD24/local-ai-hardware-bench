# TASK-008: Configurar el scrape base de Prometheus

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
| Contract tests | `monitoring.contract_tests.test_prometheus_files_contract` |
| Working directory | Repository root |

## Objetivo

Versionar `monitoring/prometheus/prometheus.yml` sin secretos: scrape cada 15 s
de `127.0.0.1:8080/metrics` con `bearer_token_file` externo y de
`127.0.0.1:9100/metrics` para node_exporter.

## Archivos

- `monitoring/prometheus/prometheus.yml`
