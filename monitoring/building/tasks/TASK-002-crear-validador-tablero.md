# TASK-002: Crear validador del tablero

| Campo | Valor |
|---|---|
| Status | `ready` |
| Owner | — |
| Created | 2026-08-28T21:41:16Z |
| Updated | 2026-08-28T21:41:16Z |
| Depends on | TASK-001 |
| Execution | `orchestrated` |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s / 2048 output / reasoning none |
| Working directory | Repository root |

## Objetivo

Crear un CLI Python de sólo lectura que detecte incoherencias entre los
documentos de `building/tasks/` y `building/TASKS.md`.

## Contexto mínimo

- Leer `monitoring/AGENTS.md`, `building/README.md`,
  `building/HERMES_TASK_GUIDE.md` y esta tarea.
- No leer auditorías ni otros worktrees.
- El orquestador gestiona estado y timestamps; no modificar `building/`.

## Contrato cerrado

Comando:

```text
python3 -m monitoring.taskctl validate --root .
```

Implementar sólo con biblioteca estándar. El validador debe:

- descubrir `monitoring/building/tasks/TASK-NNN-*.md` en orden;
- rechazar IDs o nombres duplicados y nombres que no coincidan con el ID;
- leer la primera tabla de metadatos sin aceptar filas `||`;
- exigir los campos de `TASK_TEMPLATE.md` y un estado conocido;
- exigir Owner no vacío en `in_progress` y `—` en los demás estados;
- validar timestamps ISO 8601 UTC y dependencias separadas por coma o `—`;
- comprobar que dependencias existan y no sean la propia tarea;
- comparar ID, estado, owner y dependencias con la fila de `TASKS.md`;
- comprobar que el enlace del índice apunte al fichero correcto;
- imprimir errores ordenados como `ruta: mensaje` en stderr;
- imprimir `OK: N tasks` en stdout si todo es válido.

Códigos: `0` válido, `1` incoherencias y `2` argumentos o raíz inválidos.
No escribir archivos en ninguna ruta.

## Matriz mínima de pruebas

Usar `tempfile.TemporaryDirectory` con fixtures Markdown mínimos:

| Prueba | Demuestra |
|---|---|
| Proyecto válido | Código `0` y recuento correcto |
| Tabla con `||` | Código `1` |
| Estado o owner inválido | Código `1` |
| Índice desincronizado | Código `1` |
| Dependencia ausente o propia | Código `1` |
| Enlace o nombre incorrecto | Código `1` |
| Raíz inexistente | Código `2` |

Cada caso debe invocar comportamiento real de `main(argv)` y aislar stdout y
stderr. No cambiar `sys.path`.

## Preflight

| Directorio | Comando exacto | Código esperado |
|---|---|---:|
| Raíz | `python3 --version` | Python 3.10+ |
| Raíz | `python3 -c "import pathlib, tempfile, unittest"` | `0` |
| Raíz | `python3 -m unittest discover -s monitoring/tests -p 'test_*.py'` | `0` |

## Archivos permitidos

- `monitoring/taskctl.py`
- `monitoring/tests/test_taskctl.py`

Antes de `git diff --check`, ejecutar:

```text
git add -N -- monitoring/taskctl.py monitoring/tests/test_taskctl.py
```

## Verificación obligatoria

| Directorio | Comando exacto | Código esperado |
|---|---|---:|
| Raíz | `python3 -m unittest discover -s monitoring/tests -p 'test_*.py'` | `0` |
| Raíz | `python3 -m monitoring.taskctl validate --root .` | `0` |
| Raíz | `python3 -m monitoring.taskctl --help` | `0` |
| Raíz | `git diff --check` | `0` |
| Raíz | `git status --short` | `0`; sólo archivos permitidos y estado preparado por el orquestador |

## Resultado

Entregar exclusivamente el formato de `HERMES_TASK_GUIDE.md`. `PASS` requiere
los cinco comandos en verde; no modificar esta tarea ni `TASKS.md`.
