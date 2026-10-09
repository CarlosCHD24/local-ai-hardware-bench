# TASK-011: Crear reglas de grabación de inferencia

| Campo | Valor |
|---|---|
| Status | `done` |
| Owner | — |
| Created | 2026-08-29T12:42:00Z |
| Updated | 2026-08-29T12:42:00Z |
| Depends on | TASK-008 |
| Execution | `orchestrated` |
| Execution manifest | Obligatorio por job |
| Profile | `monitoringworker` |
| Budget | Pendiente de configuración Prometheus |
| Rounds | 3 |
| Contract tests | Pendiente de fixture de series |
| Working directory | Raíz exacta indicada en el manifiesto |

## Objetivo

Añadir reglas de grabación para tokens de entrada, caché, generación y tasas
de rendimiento de `llama-server`, con tratamiento explícito de reinicios.

## Contrato cerrado

Crear `monitoring/prometheus/recording-rules.yml` con cinco reglas: entrada,
tokens totales, ratio de caché y tasas de prompt y generación. Las tasas usan
`rate(...[5m])`; el ratio devuelve cero cuando no hay entrada.

## Handoff

No debe implementar expresiones PromQL hasta que TASK-008 fije la configuración
y la herramienta de validación.
