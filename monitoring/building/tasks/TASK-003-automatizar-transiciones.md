# TASK-003: Automatizar transiciones de tareas

| Campo | Valor |
|---|---|
| Status | `ready` |
| Owner | — |
| Created | 2026-08-28T21:41:16Z |
| Updated | 2026-08-28T21:41:16Z |
| Depends on | TASK-002 |
| Execution | `orchestrated` |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s / 2048 output / reasoning none |
| Working directory | Repository root |

## Objetivo

Ampliar `taskctl` para que el orquestador reclame y envíe tareas a revisión sin
editar tablas Markdown manualmente.

## Contexto mínimo

- Leer los cuatro documentos indicados por `monitoring/AGENTS.md`,
  `building/HERMES_TASK_GUIDE.md`, TASK-002 y esta tarea.
- TASK-002 debe estar `done` y su suite en verde.
- No leer auditorías ni modificar documentos reales durante los tests.

## Contrato cerrado

Conservar `validate` y añadir:

```text
python3 -m monitoring.taskctl claim TASK-003 --owner Hermes --root .
python3 -m monitoring.taskctl submit TASK-003 --root .
```

`claim` sólo acepta una tarea `ready`, owner vacío y dependencias `done`. Debe
cambiar tarea e índice a `in_progress`, guardar owner y usar UTC real.

`submit` sólo acepta `in_progress`. Debe cambiar tarea e índice a `review`,
vaciar owner y usar UTC real. Ningún comando permite establecer `done`.

Ambos comandos deben:

- validar todo antes de escribir;
- preservar el resto de los documentos byte a byte;
- escribir mediante fichero temporal y `os.replace`;
- evitar cambios parciales si falla la segunda escritura;
- terminar ejecutando la misma validación de `validate`.

Patrón de escritura: leer ambos originales, construir ambos resultados y
escribir los dos temporales antes del primer `os.replace`. Si falla el segundo
replace, restaurar el primer original mediante otro temporal y devolver `2`.
No intentar una transacción distinta ni sobrescribir directamente los ficheros.

Códigos: `0` transición realizada, `1` estado o dependencia inválidos y `2`
argumentos, raíz o error de escritura. Errores breves en stderr.

## Patrón de pruebas

Usar un proyecto completo dentro de `TemporaryDirectory` y `mock.patch` para
reloj y `os.replace`. Verificar:

- claim válido sincroniza los dos documentos y el timestamp fijado;
- claim rechaza dependencia pendiente y owner previo sin escribir;
- submit válido limpia owner y sincroniza;
- submit rechaza cualquier estado distinto de `in_progress`;
- fallo de escritura no deja documentos desincronizados;
- no existe subcomando ni argumento que establezca `done`;
- `validate` sigue pasando después de cada transición válida.

## Preflight

| Directorio | Comando exacto | Código esperado |
|---|---|---:|
| Raíz | `python3 -m monitoring.taskctl validate --root .` | `0` |
| Raíz | `python3 -m unittest discover -s monitoring/tests -p 'test_*.py'` | `0` |

## Archivos permitidos

- `monitoring/taskctl.py`
- `monitoring/tests/test_taskctl.py`

## Verificación obligatoria

| Directorio | Comando exacto | Código esperado |
|---|---|---:|
| Raíz | `python3 -m unittest discover -s monitoring/tests -p 'test_*.py'` | `0` |
| Raíz | `python3 -m monitoring.taskctl validate --root .` | `0` |
| Raíz | `python3 -m monitoring.taskctl --help` | `0` |
| Raíz | `git diff --check` | `0` |
| Raíz | `git status --short` | `0`; sólo archivos permitidos y estado del orquestador |

## Resultado

Entregar el formato de `HERMES_TASK_GUIDE.md`. No ejecutar `claim` o `submit`
contra el repositorio real durante esta tarea; el orquestador probará después.
