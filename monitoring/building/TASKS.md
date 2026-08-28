# Estado de tareas

Este fichero ofrece una vista rápida. El estado detallado y autoritativo está
en el documento de cada tarea.

## Resumen

| ID | Tarea | Estado | Owner | Depende de |
|---|---|---|---|---|
| TASK-001 | [Crear comprobador seguro de métricas](tasks/TASK-001-crear-comprobador-metricas.md) | `done` | — | — |
| TASK-002 | [Crear validador del tablero](tasks/TASK-002-crear-validador-tablero.md) | `ready` | — | TASK-001 |
| TASK-003 | [Automatizar transiciones de tareas](tasks/TASK-003-automatizar-transiciones.md) | `ready` | — | TASK-002 |
| TASK-004 | [Crear colector de métricas NVIDIA](tasks/TASK-004-crear-colector-nvidia.md) | `ready` | — | TASK-003 |

## Próxima tarea

La primera tarea accionable es `TASK-002`. Las siguientes están completamente
definidas, pero no se reclaman hasta que sus dependencias estén `done`.

## Reglas del índice

- Una fila por tarea, ordenada por identificador.
- El título enlaza siempre al fichero de `tasks/`.
- `Owner` sólo se rellena durante `in_progress`.
- Los estados deben pertenecer al catálogo definido en [`README.md`](README.md).
