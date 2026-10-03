# TASK-006: Decidir la exposición del colector NVIDIA

| Campo | Valor |
|---|---|
| Status | `done` |
| Owner | — |
| Created | 2026-08-29T12:30:00Z |
| Updated | 2026-08-29T12:38:00Z |
| Depends on | TASK-005 |
| Execution | `orchestrated` |
| Execution manifest | Obligatorio por job |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s / 2048 output / reasoning none |
| Rounds | 3 |
| Contract tests | No aplica: decisión de arquitectura auditada |
| Working directory | Raíz exacta indicada en el manifiesto |

## Objetivo

Registrar una decisión de arquitectura que elija entre un endpoint HTTP local y
un textfile collector para publicar la salida de `monitoring.nvidia_metrics`.

## Contexto mínimo

- Leer `monitoring/README.md`, en particular las secciones 4.4 y 13.
- El colector actual ejecuta una muestra de `nvidia-smi` y no debe cambiar en
  esta tarea.
- La decisión debe mantener el servicio dentro de la red local, sin secretos ni
  contenido de inferencia en métricas o logs.

## Alcance

Incluye comparar las dos alternativas y guardar una ADR en
`monitoring/decisions/ADR-001-exposicion-nvidia.md`.

No incluye implementar el adaptador elegido, instalar Prometheus ni modificar
servicios en ejecución.

## Contrato cerrado

La ADR debe declarar una única alternativa elegida, el propietario del proceso,
la ruta o puerto local, frecuencia de actualización, comportamiento ante fallos
y el motivo por el que la alternativa descartada no se usa en el MVP. Debe
indicar expresamente que no se abre un listener fuera de localhost o la LAN.

## Preflight

| Directorio | Comando exacto | Código esperado |
|---|---|---:|
| Raíz | `python3 -m monitoring.nvidia_metrics --help` | `0` |
| Raíz | `python3 -m monitoring.taskctl validate --root .` | `0` |

## Criterios de aceptación

- [ ] La ADR resuelve HTTP frente a textfile sin dejar alternativas ambiguas.
- [ ] Define la interfaz que usará TASK-007 sin exponer secretos ni Internet.
- [ ] TASK-007 y TASK-008 se actualizan desde `draft` sólo si la ADR cierra sus
  decisiones necesarias.

## Archivos

- `monitoring/decisions/ADR-001-exposicion-nvidia.md`
- `monitoring/building/tasks/TASK-007-exponer-colector-nvidia.md`
- `monitoring/building/tasks/TASK-008-configurar-scrape-prometheus.md`

## Handoff

Aceptada como `monitoring/decisions/ADR-001-exposicion-nvidia.md`: el MVP usa
el textfile collector de `node_exporter`. TASK-007 queda preparada para
implementar el adaptador; TASK-008 conserva decisiones de despliegue propias.
