# TASK-012: Crear alertas iniciales de observabilidad

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
| Contract tests | Pendiente de fixture de reglas |
| Working directory | Raíz exacta indicada en el manifiesto |

## Objetivo

Definir alertas reproducibles para caída de `llama-server`, ausencia de scrape,
presión de VRAM, temperatura y espacio de disco.

## Contrato cerrado

Crear `monitoring/prometheus/alert-rules.yml` sólo con alertas objetivas:
`up == 0` para llama-server y node-exporter durante dos minutos. Los umbrales
de GPU, VRAM y disco permanecen fuera de alcance hasta observar una línea base.

## Handoff

La tarea queda separada de las reglas de grabación para que los umbrales y la
notificación puedan revisarse independientemente.
