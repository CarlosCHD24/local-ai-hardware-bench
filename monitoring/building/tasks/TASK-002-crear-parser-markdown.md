# TASK-002: Crear parser de tablas Markdown

| Campo | Valor |
|---|---|
| Status | `ready` |
| Owner | — |
| Created | 2026-08-28T22:52:58Z |
| Updated | 2026-08-28T22:52:58Z |
| Depends on | TASK-001 |
| Execution | `orchestrated` |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s / 2048 output / reasoning none |
| Rounds | 3 |
| Contract tests | `monitoring.contract_tests.test_markdown_table_contract` |
| Working directory | Repository root |

## Objetivo

Crear un parser pequeño y determinista para la primera tabla Markdown estándar
de un texto, sin incorporar todavía reglas de tareas ni del tablero.

## Contexto mínimo

- Leer `monitoring/AGENTS.md`, `building/README.md`,
  `building/HERMES_TASK_GUIDE.md` y esta tarea.
- Los tests de contrato son inmutables y no están dentro del alcance.
- El orquestador gestiona estado, rondas y timestamps.

## Contrato cerrado

Implementar con biblioteca estándar:

```python
class TableFormatError(ValueError): ...
def parse_first_table(text: str) -> tuple[list[str], list[list[str]]]: ...
```

La función busca la primera tabla, devuelve cabeceras y filas sin la línea
separadora, elimina sólo espacios exteriores y conserva backticks y texto.
Exige al menos una fila de datos, el mismo número de columnas y separadores
`---` con dos puntos opcionales. Una línea vacía o no tabular termina la tabla.
Cada celda separadora se valida de forma independiente con el patrón equivalente
a `^:?-{3,}:?$`; `:---:`, `---` y `-----` son válidos en la misma fila.

Formato válido literal:

```markdown
| Campo | Valor |
|---|---|
| Status | `ready` |
```

Formato inválido literal, que debe lanzar `TableFormatError`:

```markdown
|| Campo | Valor ||
```

También lanza `TableFormatError` si no hay tabla, el separador es inválido, no
hay datos o una fila tiene distinto número de columnas. No leer ni escribir
archivos y no añadir CLI.

## Preflight

| Directorio | Comando exacto | Código esperado |
|---|---|---:|
| Raíz | `pwd` | Raíz autorizada |
| Raíz | `python3 --version` | Python 3.10+ |
| Raíz | `python3 -m py_compile monitoring/contract_tests/test_markdown_table_contract.py` | `0` |
| Raíz | `python3 -m unittest discover -s monitoring/tests -p 'test_*.py'` | `0` |

## Archivos permitidos

- `monitoring/markdown_table.py`

No crear tests adicionales: el contrato inmutable cubre toda la matriz. No
modificar `monitoring/contract_tests/` ni `monitoring/building/`.

## Verificación obligatoria

| Directorio | Comando exacto | Código esperado |
|---|---|---:|
| Raíz | `python3 -m unittest monitoring.contract_tests.test_markdown_table_contract` | `0` |
| Raíz | `python3 -m unittest discover -s monitoring/tests -p 'test_*.py'` | `0` |
| Raíz | `git diff --check` | `0` |
| Raíz | `git status --short` | `0`; sólo archivos permitidos y estado preparado por el orquestador |

## Resultado

Entregar el formato breve de `HERMES_TASK_GUIDE.md`. No cambiar el tablero ni
marcar la tarea como terminada.

## Handoff

Sin trabajo pendiente ni bloqueos.
