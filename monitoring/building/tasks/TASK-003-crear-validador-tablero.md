# TASK-003: Crear validador del tablero

| Campo | Valor |
|---|---|
| Status | `ready` |
| Owner | — |
| Created | 2026-08-28T22:52:58Z |
| Updated | 2026-08-28T22:52:58Z |
| Depends on | TASK-002 |
| Execution | `orchestrated` |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s / 2048 output / reasoning none |
| Rounds | 3 |
| Contract tests | `monitoring.contract_tests.test_taskctl_contract` |
| Working directory | Repository root |

## Objetivo

Crear un CLI de sólo lectura que use `monitoring.markdown_table` para detectar
incoherencias entre tareas y `TASKS.md`.

## Contrato cerrado

Comando exacto desde la raíz:

```text
python3 -m monitoring.taskctl validate --root .
```

`--root` es la raíz del repositorio. Las rutas exactas son:

```text
./monitoring/building/TASKS.md
./monitoring/building/tasks/TASK-NNN-*.md
```

El CLI debe:

- descubrir tareas en orden y exigir los campos de `TASK_TEMPLATE.md`;
- validar estado, owner, timestamps UTC y dependencias existentes no propias;
- detectar IDs y nombres de fichero duplicados o inválidos;
- comparar estado, owner, dependencias y enlace con el índice;
- imprimir errores ordenados como `ruta: mensaje` en stderr;
- imprimir `OK: N tasks` en stdout si todo es válido.

Usar el parser de TASK-002; no implementar otro parser. Códigos: `0` válido,
`1` incoherencias y `2` argumentos, raíz o estructura inexistente. No escribir
archivos.

El fixture válido usa exclusivamente tablas con una barra `|`, exactamente como
los documentos reales. Cualquier fila que empiece con `||` es inválida.

## Preflight

| Directorio | Comando exacto | Código esperado |
|---|---|---:|
| Raíz | `python3 -m unittest monitoring.contract_tests.test_markdown_table_contract` | `0` |
| Raíz | `python3 -m py_compile monitoring/contract_tests/test_taskctl_contract.py` | `0` |
| Raíz | `python3 -m unittest discover -s monitoring/tests -p 'test_*.py'` | `0` |

## Archivos permitidos

- `monitoring/taskctl.py`

No crear tests adicionales ni modificar los tests de contrato o documentos de
`building/`.

## Verificación obligatoria

| Directorio | Comando exacto | Código esperado |
|---|---|---:|
| Raíz | `python3 -m unittest monitoring.contract_tests.test_taskctl_contract` | `0` |
| Raíz | `python3 -m unittest discover -s monitoring/tests -p 'test_*.py'` | `0` |
| Raíz | `python3 -m monitoring.taskctl validate --root .` | `0` |
| Raíz | `python3 -m monitoring.taskctl --help` | `0` |
| Raíz | `git diff --check` | `0` |

## Resultado

Entregar el formato de `HERMES_TASK_GUIDE.md`; la auditoría mecánica decide si
se habilita TASK-004.

## Handoff

Sin trabajo pendiente ni bloqueos.
