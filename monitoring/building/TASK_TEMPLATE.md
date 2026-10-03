# TASK-NNN: Título en infinitivo

| Campo | Valor |
|---|---|
| Status | `draft` |
| Owner | — |
| Created | AAAA-MM-DDTHH:MM:SSZ |
| Updated | AAAA-MM-DDTHH:MM:SSZ |
| Depends on | — |
| Execution | `orchestrated` |
| Execution manifest | Generado desde `building/JOB_MANIFEST_TEMPLATE.md` |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s / 2048 output / reasoning none |
| Rounds | 3 |
| Contract tests | Ruta inmutable ejecutada por el orquestador |
| Working directory | Repository root |

## Objetivo

Una frase que describa el resultado observable de esta tarea.

## Contexto mínimo

- Documentos o rutas que el ejecutor necesita leer.
- Decisiones ya tomadas que no debe volver a abrir.
- No leer auditorías históricas ni otros worktrees.
- Validar primero el manifiesto del job; no trabajar sobre una rama móvil.

## Alcance

Incluye:

- Cambio concreto incluido.

No incluye:

- Cambio próximo o relacionado que pertenece a otra tarea.

## Contrato cerrado

- Comando, función o archivo exacto que se entrega.
- Entradas, salidas, unidades y orden determinista.
- Errores y códigos de salida sin decisiones pendientes.
- Efectos externos permitidos y prohibidos.
- Ejemplo literal válido y ejemplo literal inválido para cada formato.

## Preflight

El preflight Git exacto se genera en el manifiesto. Debe pasar antes de estos
controles específicos y demostrar rama, commits, referencia remota y worktree
limpio.

| Directorio | Comando exacto | Código esperado |
|---|---|---:|
| Raíz del repositorio | Comando seguro que valide el entorno | `0` |

## Pasos

- [ ] Paso principal 1.
- [ ] Paso principal 2.
- [ ] Ejecutar las verificaciones.
- [ ] Entregar resultado con el formato de `HERMES_TASK_GUIDE.md`.

## Criterios de aceptación

- [ ] Resultado comprobable 1.
- [ ] Resultado comprobable 2.

## Matriz mínima de pruebas

| Prueba | Requisito que demuestra |
|---|---|
| Nombre exacto | Comportamiento y resultado esperado |

Cuando haya mocks, tiempo, red o escritura, incluir un fixture o patrón mínimo
que el ejecutor deba reutilizar.

Los tests de contrato ya existen, están fuera de `Archivos` y Hermes no puede
modificarlos. El orquestador los ejecuta al terminar cada ronda. No solicitar un
archivo de tests duplicado cuando el contrato cubra toda la matriz.

## Verificación

| Directorio | Comando exacto | Código esperado |
|---|---|---:|
| Raíz del repositorio | Comando reproducible | `0` |

Para archivos nuevos, ejecutar primero `git add -N -- rutas-permitidas` y después
`git diff --check`.

## Evidencias

| Directorio real | Comando | Código | Resultado breve |
|---|---|---:|---|
| Pendiente | Pendiente | — | Pendiente |

## Archivos

- Rutas técnicas exactas que Hermes puede modificar.
- En modo `orchestrated`, nunca incluir `building/`.

## Decisiones

- Ninguna.

## Handoff

Sin trabajo pendiente ni bloqueos.
