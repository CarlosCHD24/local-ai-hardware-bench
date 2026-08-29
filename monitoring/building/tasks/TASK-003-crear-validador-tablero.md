# TASK-003: Crear validador del tablero

| Campo | Valor |
|---|---|
| Status | `in_progress` |
| Owner | Hermes |
| Created | 2026-08-28T22:52:58Z |
| Updated | 2026-08-29T10:09:19Z |
| Depends on | TASK-002 |
| Execution | `orchestrated` |
| Execution manifest | Obligatorio por job |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s / 2048 output / reasoning none |
| Rounds | 3 |
| Contract tests | `monitoring.contract_tests.test_taskctl_contract` |
| Working directory | Raíz exacta indicada en el manifiesto |

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

## Pista para el reintento

El primer argumento posicional es una suborden obligatoria. Crear un subparser
`validate` y añadir `--root` a ese subparser; debe funcionar exactamente:

```python
subparsers = parser.add_subparsers(dest="command", required=True)
validate_parser = subparsers.add_parser("validate")
validate_parser.add_argument("--root", default=".")
```

No basta con corregir `argparse`. Reparar también estos fallos ya presentes:

1. Descubrir cada ruta `TASK-NNN-slug.md` y extraer ID y slug con una expresión
   que conserve `TASK-001` completo; `split("-")[0]` devuelve sólo `TASK`.
2. Guardar las tareas por ID con su `Path` y metadatos. Iterar sobre esos
   objetos, nunca sobre valores booleanos.
3. Parsear `TASKS.md` con `monitoring.markdown_table.parse_first_table`. Sus
   columnas son `ID`, `Tarea`, `Estado`, `Owner` y `Depende de`; extraer del
   enlace Markdown tanto el texto como `tasks/TASK-NNN-slug.md`.
4. Quitar exactamente un par de backticks al comparar estados como `ready` o
   `done`. Para cualquier estado distinto de `in_progress`, el owner debe ser
   `—`; `in_progress` requiere owner no vacío y distinto de `—`.
5. Comparar por ID el estado, owner, dependencia y enlace de índice contra el
   documento. Comprobar dependencia existente y distinta de la propia tarea.
6. Acumular todos los errores como `ruta: mensaje`, ordenarlos y devolver `1`.
   Devolver `2` sólo para argumentos, raíz o estructura inexistente.

Ejecutar primero el test completo del contrato. No informar `PASS` mientras
alguna invocación `main(["validate", "--root", ...])` produzca `SystemExit`.

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

Reabierta con una pista focalizada para tres nuevas rondas.
