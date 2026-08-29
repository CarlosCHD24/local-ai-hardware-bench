"""Validador del tablero de tareas."""

import argparse
import re
import sys
from pathlib import Path

from monitoring import markdown_table


# Estados válidos
VALID_STATES = {"draft", "ready", "in_progress", "blocked", "review", "done", "cancelled"}

# Patrón para timestamps UTC ISO 8601
ISO8601_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def parse_task_file(path: Path) -> dict:
    """
    Parsea un archivo de tarea y extrae los metadatos de la tabla.

    Devuelve un dict con los campos o lanza TableFormatError si el formato es inválido.
    """
    content = path.read_text(encoding="utf-8")

    # Extraer la primera tabla
    header, rows = markdown_table.parse_first_table(content)

    # Validar cabeceras
    if header != ["Campo", "Valor"]:
        raise ValueError(f"Tabla inválida: cabeceras '{header}' != ['Campo', 'Valor']")

    # Construir el dict de metadatos
    metadata = {}
    for row in rows:
        if len(row) != 2:
            raise ValueError(f"Fila inválida: {row}")
        key, value = row
        metadata[key] = value

    return metadata


def validate_task_file(path: Path, index: dict) -> list[str]:
    """
    Valida un archivo de tarea individual.

    Devuelve una lista de errores (o lista vacía si es válido).
    """
    errors = []

    try:
        metadata = parse_task_file(path)
    except markdown_table.TableFormatError as e:
        return [f"tabla: {e}"]
    except ValueError as e:
        return [f"formato: {e}"]

    # Extraer campos
    status = metadata.get("Status", "")
    owner = metadata.get("Owner", "")
    created = metadata.get("Created", "")
    updated = metadata.get("Updated", "")
    depends = metadata.get("Depends on", "")

    # Validar que la tabla use una sola barra (no ||)
    content = path.read_text(encoding="utf-8")
    if "||" in content:
        errors.append("tabla: formato inválido: celdas vacías no permitidas (||)")

    # Limpiar backticks del estado antes de validar
    # Validar estado
    if status not in VALID_STATES:
        errors.append(f"estado: '{status}' no válido. Debe ser uno de: {', '.join(sorted(VALID_STATES))}")

    # Validar owner (puede ser "—" o cualquier string)
    # No hay restricción específica para owner

    # Validar timestamps UTC ISO 8601
    for ts_field in ("Created", "Updated"):
        ts_value = metadata.get(ts_field, "")
        if ts_value and not ISO8601_PATTERN.match(ts_value):
            errors.append(f"{ts_field}: '{ts_value}' no es un timestamp UTC ISO 8601 válido")

    # Validar dependencias
    if depends and depends != "—":
        # La dependencia no puede ser la tarea misma
        task_id = path.stem  # Ej: TASK-003-crear-validador-tablero -> TASK-003-crear-validador-tablero
        # Extraer el ID de la tarea (parte antes del primer guion)
        task_id_base = task_id.split("-")[0]
        if depends == task_id_base:
            errors.append(f"dependencia: no puede depender de sí misma ({depends})")
        elif depends not in index:
            errors.append(f"dependencia: '{depends}' no existe en el índice")

    return errors


def validate_index_consistency(index: dict, tasks: dict) -> list[str]:
    """
    Valida que el índice sea consistente con los archivos de tarea.

    Devuelve una lista de errores.
    """
    errors = []

    for task_id, slug in index.items():
        expected_path = Path(f"monitoring/building/tasks/{task_id}-{slug}.md")
        if expected_path not in tasks:
            errors.append(f"{task_id}: enlace en índice incorrecto (esperado: {expected_path})")

    return errors


def main(argv=None):
    """Entrada principal del CLI."""
    parser = argparse.ArgumentParser(
        prog="taskctl",
        description="Validador del tablero de tareas"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument(
        "--root",
        type=str,
        default=".",
        help="Raíz del repositorio (default: .)"
    )

    args = parser.parse_args(argv)

    if args.command != "validate":
        parser.error(f"Comando desconocido: {args.command}")

    root = Path(args.root)

    # Validar que la raíz existe
    if not root.exists():
        print(f"Error: ruta '{root}' no existe", file=sys.stderr)
        return 2

    if not root.is_dir():
        print(f"Error: '{root}' no es un directorio", file=sys.stderr)
        return 2

    # Construir el índice de tareas
    index = {}
    tasks = {}

    tasks_dir = root / "monitoring" / "building" / "tasks"
    if not tasks_dir.exists():
        print(f"Error: directorio de tareas '{tasks_dir}' no existe", file=sys.stderr)
        return 2

    # Leer el índice TASKS.md
    tasks_md = root / "monitoring" / "building" / "TASKS.md"
    if tasks_md.exists():
        try:
            content = tasks_md.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            # Buscar la tabla del índice
            in_table = False
            for line in lines:
                if line.startswith("| ID | Tarea |"):
                    in_table = True
                    continue
                if in_table and line.startswith("|") and "|" in line:
                    # Parsear fila del índice
                    cells = [c.strip() for c in line.split("|")]
                    if len(cells) >= 6:
                        task_id = cells[1]
                        # Extraer slug del enlace: [título](tasks/slug.md) -> slug
                        link = cells[2].split("]")[1]  # Extraer enlace: (tasks/slug.md)
                        slug = link[1:].split("tasks/")[1].rsplit(".md")[0]  # Extraer slug
                        status = cells[3].strip().strip("`")  # Quitar backticks
                        owner = cells[4]
                        depends = cells[5]
                        index[task_id] = slug
        except Exception as e:
            print(f"Error al leer TASKS.md: {e}", file=sys.stderr)
            return 2

    # Descubrir tareas en orden
    for f in sorted(tasks_dir.iterdir()):
        if f.is_file() and f.suffix == ".md":
            tasks[f] = f

    # Validar cada archivo de tarea
    all_errors = []

    for path in sorted(tasks.values()):
        errors = validate_task_file(path, index)
        all_errors.extend(errors)

    # Validar consistencia del índice
    index_errors = validate_index_consistency(index, tasks)
    all_errors.extend(index_errors)

    # Reportar errores
    if all_errors:
        for error in all_errors:
            print(error, file=sys.stderr)
        return 1

    print(f"OK: {len(tasks)} tasks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
