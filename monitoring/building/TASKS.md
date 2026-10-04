# Estado de tareas

Este fichero ofrece una vista rápida. El estado detallado y autoritativo está
en el documento de cada tarea.

## Resumen

| ID | Tarea | Estado | Owner | Depende de |
|---|---|---|---|---|
| TASK-001 | [Crear comprobador seguro de métricas](tasks/TASK-001-crear-comprobador-metricas.md) | `done` | — | — |
| TASK-002 | [Crear parser de tablas Markdown](tasks/TASK-002-crear-parser-markdown.md) | `done` | — | TASK-001 |
| TASK-003 | [Crear validador del tablero](tasks/TASK-003-crear-validador-tablero.md) | `done` | — | TASK-002 |
| TASK-004 | [Automatizar transiciones de tareas](tasks/TASK-004-automatizar-transiciones.md) | `done` | — | TASK-003 |
| TASK-005 | [Crear colector de métricas NVIDIA](tasks/TASK-005-crear-colector-nvidia.md) | `done` | — | TASK-004 |
| TASK-006 | [Decidir la exposición del colector NVIDIA](tasks/TASK-006-decidir-exposicion-nvidia.md) | `done` | — | TASK-005 |
| TASK-007 | [Exponer el colector NVIDIA para Prometheus](tasks/TASK-007-exponer-colector-nvidia.md) | `done` | — | TASK-006 |
| TASK-008 | [Configurar el scrape base de Prometheus](tasks/TASK-008-configurar-scrape-prometheus.md) | `done` | — | TASK-006 |
| TASK-009 | [Validar la configuración de Prometheus](tasks/TASK-009-definir-contrato-textfile.md) | `done` | — | TASK-008 |
| TASK-010 | [Preparar el servicio de node_exporter](tasks/TASK-010-preparar-node-exporter.md) | `done` | — | TASK-007 |
| TASK-011 | [Crear reglas de grabación de inferencia](tasks/TASK-011-crear-reglas-inferencia.md) | `done` | — | TASK-008 |
| TASK-012 | [Crear alertas iniciales de observabilidad](tasks/TASK-012-crear-alertas-observabilidad.md) | `done` | — | TASK-008 |
| TASK-013 | [Provisionar la fuente de datos Grafana](tasks/TASK-013-provisionar-grafana.md) | `done` | — | TASK-008 |
| TASK-014 | [Crear dashboard base de inferencia](tasks/TASK-014-dashboard-inferencia.md) | `done` | — | TASK-011 |
| TASK-015 | [Programar la muestra NVIDIA](tasks/TASK-015-programar-muestra-nvidia.md) | `done` | — | TASK-007 |
| TASK-016 | [Crear temporizador NVIDIA](tasks/TASK-016-crear-temporizador-nvidia.md) | `done` | — | TASK-015 |
| TASK-017 | [Documentar el despliegue de monitoring](tasks/TASK-017-documentar-despliegue.md) | `done` | — | TASK-010 |
| TASK-018 | [Validar artefactos operativos](tasks/TASK-018-validar-operacion.md) | `done` | — | TASK-015 |
| TASK-019 | [Reconciliar documentación y despliegue](tasks/TASK-019-reconciliar-despliegue.md) | `done` | — | TASK-018 |
| TASK-020 | [Medir frescura del colector NVIDIA](tasks/TASK-020-medir-frescura-nvidia.md) | `draft` | — | TASK-019 |
| TASK-021 | [Capturar línea base de hardware](tasks/TASK-021-capturar-linea-base.md) | `draft` | — | TASK-020 |
| TASK-022 | [Definir alertas de capacidad](tasks/TASK-022-definir-alertas-capacidad.md) | `draft` | — | TASK-021 |
| TASK-023 | [Modelar energía y coste GPU](tasks/TASK-023-modelar-energia-coste.md) | `draft` | — | TASK-021 |
| TASK-024 | [Decidir entrega de alertas](tasks/TASK-024-decidir-entrega-alertas.md) | `draft` | — | TASK-022 |

## Próxima tarea

No hay tareas accionables. `TASK-019` está en `review` y `TASK-020`..
`TASK-024` siguen en `draft` a la espera de contrato, línea base o decisión
explícita.

## Reglas del índice

- Una fila por tarea, ordenada por identificador.
- El título enlaza siempre al fichero de `tasks/`.
- `Owner` sólo se rellena durante `in_progress`.
- Los estados deben pertenecer al catálogo definido en [`README.md`](README.md).
