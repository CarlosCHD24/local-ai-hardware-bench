# TASK-004: Automatizar transiciones de tareas

| Campo | Valor |
|---|---|
| Status | `ready` |
| Owner | — |
| Created | 2026-08-28T22:52:58Z |
| Updated | 2026-08-28T22:52:58Z |
| Depends on | TASK-003 |
| Execution | `orchestrated` |
| Execution manifest | Obligatorio por job |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s / 2048 output / reasoning none |
| Rounds | 3 |
| Contract tests | `monitoring.contract_tests.test_taskctl_transitions_contract` |
| Working directory | Raíz exacta indicada en el manifiesto |

## Objetivo

Ampliar `taskctl` con transiciones atómicas `claim` y `submit` para uso del
orquestador.

## Contrato cerrado

Conservar `validate` y añadir:

```text
python3 -m monitoring.taskctl claim TASK-004 --owner Hermes --root .
python3 -m monitoring.taskctl submit TASK-004 --root .
```

`claim` sólo acepta `ready`, owner vacío y dependencias `done`; cambia tarea e
índice a `in_progress`, guarda owner y UTC. `submit` sólo acepta `in_progress`;
cambia ambos a `review`, limpia owner y usa UTC. No existe transición a `done`.

Validar antes y después. Construir los dos temporales antes del primer
`os.replace`. Si falla el segundo replace, restaurar el primer original mediante
otro temporal y devolver `2`. Códigos de transición: `0` éxito, `1` estado o
dependencia inválidos y `2` argumentos, raíz o escritura.

Los tests usan un repositorio temporal, `mock.patch` sobre `utc_now` y
`os.replace`, y nunca ejecutan las transiciones contra el repositorio real.

## Preflight

| Directorio | Comando exacto | Código esperado |
|---|---|---:|
| Raíz | `python3 -m monitoring.taskctl validate --root .` | `0` |
| Raíz | `python3 -m py_compile monitoring/contract_tests/test_taskctl_transitions_contract.py` | `0` |

## Archivos permitidos

- `monitoring/taskctl.py`

No crear tests adicionales ni modificar los tests de contrato.

## Verificación obligatoria

| Directorio | Comando exacto | Código esperado |
|---|---|---:|
| Raíz | `python3 -m unittest monitoring.contract_tests.test_taskctl_contract monitoring.contract_tests.test_taskctl_transitions_contract` | `0` |
| Raíz | `python3 -m unittest discover -s monitoring/tests -p 'test_*.py'` | `0` |
| Raíz | `python3 -m monitoring.taskctl validate --root .` | `0` |
| Raíz | `python3 -m monitoring.taskctl --help` | `0` |
| Raíz | `git diff --check` | `0` |

## Resultado

Entregar el formato de `HERMES_TASK_GUIDE.md`. No ejecutar `claim` o `submit`
contra el repositorio real.

## Handoff

Sin trabajo pendiente ni bloqueos.
