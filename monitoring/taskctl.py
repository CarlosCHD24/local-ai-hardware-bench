"""Validador y transiciones atómicas del tablero de tareas."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from monitoring import markdown_table
from src.local_ai_bench.system.common import utc_now


VALID_STATES = {
    "draft",
    "ready",
    "in_progress",
    "blocked",
    "review",
    "done",
    "cancelled",
}
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
TASK_NAME_RE = re.compile(r"^(TASK-\d{3})-(.+)\.md$")
TASK_LINK_RE = re.compile(r"^\[([^\]]+)\]\((tasks/(TASK-\d{3})-[^)]+\.md)\)$")
TASK_FIELDS = (
    "Status",
    "Owner",
    "Created",
    "Updated",
    "Depends on",
    "Execution",
    "Profile",
    "Budget",
    "Rounds",
    "Contract tests",
    "Working directory",
)
INDEX_HEADER = ["ID", "Tarea", "Estado", "Owner", "Depende de"]


def unquote(value: str) -> str:
    """Elimina un único par de backticks Markdown, si lo hay."""
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        return value[1:-1]
    return value


def parse_task_file(path: Path) -> dict[str, str]:
    """Lee la tabla de metadatos de una tarea usando el parser compartido."""
    header, rows = markdown_table.parse_first_table(path.read_text(encoding="utf-8"))
    if header != ["Campo", "Valor"]:
        raise ValueError("cabecera de metadatos inválida")

    metadata: dict[str, str] = {}
    for row in rows:
        if len(row) != 2:
            raise ValueError("fila de metadatos inválida")
        key, value = row
        if key in metadata:
            raise ValueError(f"campo duplicado: {key}")
        metadata[key] = value
    return metadata


def task_errors(path: Path, metadata: dict[str, str], known_ids: set[str]) -> list[str]:
    """Devuelve las incoherencias del documento de una tarea."""
    errors: list[str] = []
    task_match = TASK_NAME_RE.fullmatch(path.name)
    task_id = task_match.group(1) if task_match else path.stem

    for field in TASK_FIELDS:
        if field not in metadata:
            errors.append(f"falta el campo {field}")

    status = unquote(metadata.get("Status", ""))
    owner = metadata.get("Owner", "")
    depends_on = unquote(metadata.get("Depends on", ""))

    if status not in VALID_STATES:
        errors.append(f"estado no válido: {status!r}")
    if status == "in_progress":
        if not owner or owner == "—":
            errors.append("owner obligatorio durante in_progress")
    elif owner != "—":
        errors.append("owner debe ser — fuera de in_progress")

    for field in ("Created", "Updated"):
        value = metadata.get(field, "")
        if not TIMESTAMP_RE.fullmatch(value):
            errors.append(f"{field} no es un timestamp UTC válido")

    if depends_on not in ("", "—"):
        if depends_on == task_id:
            errors.append("dependencia propia no permitida")
        elif depends_on not in known_ids:
            errors.append(f"dependencia inexistente: {depends_on}")
    return errors


def parse_index(path: Path) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Devuelve las filas estructuradas del índice y los errores de formato."""
    try:
        header, rows = markdown_table.parse_first_table(path.read_text(encoding="utf-8"))
    except (OSError, markdown_table.TableFormatError) as error:
        return {}, [f"tabla: {error}"]

    if header != INDEX_HEADER:
        return {}, ["tabla: cabecera del índice inválida"]

    index: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    for row in rows:
        if len(row) != 5:
            errors.append("tabla: fila del índice con número de columnas inválido")
            continue
        task_id, link, status, owner, depends_on = row
        link_match = TASK_LINK_RE.fullmatch(link)
        if not re.fullmatch(r"TASK-\d{3}", task_id):
            errors.append(f"ID de índice inválido: {task_id!r}")
            continue
        if link_match is None:
            errors.append(f"{task_id}: enlace de tarea inválido")
            continue
        if link_match.group(3) != task_id:
            errors.append(f"{task_id}: enlace apunta a otro ID")
        if task_id in index:
            errors.append(f"{task_id}: ID duplicado en el índice")
            continue
        index[task_id] = {
            "link": link,
            "path": link_match.group(2),
            "status": unquote(status),
            "owner": owner,
            "depends": unquote(depends_on),
        }
    return index, errors


def validate(root: Path) -> tuple[int, list[str], int]:
    """Valida el tablero y devuelve código, errores y número de tareas."""
    tasks_dir = root / "monitoring" / "building" / "tasks"
    index_path = root / "monitoring" / "building" / "TASKS.md"
    if not root.is_dir() or not tasks_dir.is_dir() or not index_path.is_file():
        return 2, ["estructura del repositorio inexistente"], 0

    task_paths = sorted(path for path in tasks_dir.iterdir() if path.is_file() and path.suffix == ".md")
    tasks: dict[str, dict[str, object]] = {}
    errors: list[str] = []
    for path in task_paths:
        match = TASK_NAME_RE.fullmatch(path.name)
        relative = path.relative_to(root).as_posix()
        if match is None:
            errors.append(f"{relative}: nombre de fichero de tarea inválido")
            continue
        task_id = match.group(1)
        if task_id in tasks:
            errors.append(f"{relative}: ID de tarea duplicado: {task_id}")
            continue
        try:
            metadata = parse_task_file(path)
        except (OSError, markdown_table.TableFormatError, ValueError) as error:
            errors.append(f"{relative}: tabla: {error}")
            continue
        tasks[task_id] = {"path": path, "metadata": metadata}

    index, index_errors = parse_index(index_path)
    errors.extend(f"monitoring/building/TASKS.md: {error}" for error in index_errors)
    known_ids = set(tasks)

    for task_id, task in tasks.items():
        path = task["path"]
        metadata = task["metadata"]
        assert isinstance(path, Path)
        assert isinstance(metadata, dict)
        relative = path.relative_to(root).as_posix()
        errors.extend(f"{relative}: {error}" for error in task_errors(path, metadata, known_ids))

        row = index.get(task_id)
        if row is None:
            errors.append(f"{relative}: {task_id} no aparece en TASKS.md")
            continue
        expected_link = f"tasks/{path.name}"
        if row["path"] != expected_link:
            errors.append(f"{relative}: {task_id} tiene un enlace de índice incorrecto")
        if row["status"] != unquote(metadata.get("Status", "")):
            errors.append(f"{relative}: {task_id} tiene estado distinto en TASKS.md")
        if row["owner"] != metadata.get("Owner", ""):
            errors.append(f"{relative}: {task_id} tiene owner distinto en TASKS.md")
        if row["depends"] != unquote(metadata.get("Depends on", "")):
            errors.append(f"{relative}: {task_id} tiene dependencia distinta en TASKS.md")

    for task_id in index:
        if task_id not in tasks:
            errors.append(f"monitoring/building/TASKS.md: {task_id} no tiene fichero de tarea")

    return (1 if errors else 0), sorted(errors), len(tasks)


def claim_task(task_id: str, owner: str, root: Path) -> int:
    """Transición claim: ready -> in_progress."""
    tasks_dir = root / "monitoring" / "building" / "tasks"
    index_path = root / "monitoring" / "building" / "TASKS.md"
    task_path = tasks_dir / f"{task_id}.md"

    if not task_path.is_file():
        return 1

    try:
        metadata = parse_task_file(task_path)
    except (OSError, markdown_table.TableFormatError, ValueError) as error:
        print(f"error leyendo tarea: {error}", file=sys.stderr)
        return 1

    # Validar estado actual
    current_status = unquote(metadata.get("Status", ""))
    if current_status != "ready":
        print(f"error: tarea {task_id} no está en estado 'ready' (actual: {current_status})", file=sys.stderr)
        return 1

    # Validar dependencias
    depends_on = unquote(metadata.get("Depends on", ""))
    if depends_on not in ("", "—"):
        # Verificar que la dependencia esté en estado done
        dep_task_path = tasks_dir / f"{depends_on}.md"
        if dep_task_path.is_file():
            try:
                dep_metadata = parse_task_file(dep_task_path)
                dep_status = unquote(dep_metadata.get("Status", ""))
                if dep_status != "done":
                    print(f"error: dependencia {depends_on} no está en estado 'done' (actual: {dep_status})", file=sys.stderr)
                    return 1
            except (OSError, markdown_table.TableFormatError, ValueError):
                print(f"error: no se pudo leer la dependencia {depends_on}", file=sys.stderr)
                return 1

    # Validar owner
    if not owner or owner == "—":
        print("error: claim requiere owner", file=sys.stderr)
        return 1

    # Construir nuevo contenido de la tarea
    updated = utc_now()
    new_task_content = f"""# {task_id}

| Campo | Valor |
|---|---|
| Status | `in_progress` |
| Owner | {owner} |
| Created | {metadata.get("Created", "")} |
| Updated | {updated} |
| Depends on | {metadata.get("Depends on", "")} |
| Execution | `orchestrated` |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s / 2048 output / reasoning none |
| Rounds | 3 |
| Contract tests | `monitoring.contract_tests.example` |
| Working directory | Repository root |
"""

    # Construir nuevo contenido del índice
    index_lines = [
        "# Estado de tareas",
        "",
        "| ID | Tarea | Estado | Owner | Depende de |",
        "|---|---|---|---|---|",
    ]
    for row in markdown_table.parse_first_table(index_path.read_text(encoding="utf-8"))[1]:
        if len(row) == 5:
            tid, link, status, o, dep = row
            if tid == task_id:
                index_lines.append(f"| {tid} | [{link}](tasks/{link}) | `in_progress` | {owner} | {dep} |")
            else:
                index_lines.append(f"| {tid} | [{link}](tasks/{link}) | `{status}` | {o} | {dep} |")

    # Crear temporales
    temp_task = task_path.with_suffix(".md.tmp")
    temp_index = index_path.with_suffix(".md.tmp")

    try:
        temp_task.write_text(new_task_content, encoding="utf-8")
        temp_index.write_text("\n".join(index_lines) + "\n", encoding="utf-8")

        # Atomic replace
        shutil.move(str(temp_task), str(task_path))
        shutil.move(str(temp_index), str(index_path))
    except OSError as error:
        print(f"error escribiendo: {error}", file=sys.stderr)
        # Restaurar si falló
        if temp_task.exists():
            try:
                shutil.move(str(temp_task), str(task_path))
            except OSError:
                temp_task.unlink()
        if temp_index.exists():
            try:
                shutil.move(str(temp_index), str(index_path))
            except OSError:
                temp_index.unlink()
        # Restaurar originales si los temporales no se movieron
        if task_path.exists() and task_path.suffix == ".md.tmp":
            task_path.rename(task_path.with_suffix(".md"))
        if index_path.exists() and index_path.suffix == ".md.tmp":
            index_path.rename(index_path.with_suffix(".md"))
        return 2

    return 0


def submit_task(task_id: str, root: Path) -> int:
    """Transición submit: in_progress -> review."""
    tasks_dir = root / "monitoring" / "building" / "tasks"
    index_path = root / "monitoring" / "building" / "TASKS.md"
    task_path = tasks_dir / f"{task_id}.md"

    if not task_path.is_file():
        return 1

    try:
        metadata = parse_task_file(task_path)
    except (OSError, markdown_table.TableFormatError, ValueError) as error:
        print(f"error leyendo tarea: {error}", file=sys.stderr)
        return 1

    # Validar estado actual
    current_status = unquote(metadata.get("Status", ""))
    if current_status != "in_progress":
        print(f"error: tarea {task_id} no está en estado 'in_progress' (actual: {current_status})", file=sys.stderr)
        return 1

    # Validar que tenga owner
    owner = metadata.get("Owner", "")
    if not owner or owner == "—":
        print("error: submit requiere owner establecido", file=sys.stderr)
        return 1

    # Construir nuevo contenido de la tarea
    updated = utc_now()
    new_task_content = f"""# {task_id}

| Campo | Valor |
|---|---|
| Status | `review` |
| Owner | — |
| Created | {metadata.get("Created", "")} |
| Updated | {updated} |
| Depends on | {metadata.get("Depends on", "")} |
| Execution | `orchestrated` |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s / 2048 output / reasoning none |
| Rounds | 3 |
| Contract tests | `monitoring.contract_tests.example` |
| Working directory | Repository root |
"""

    # Construir nuevo contenido del índice
    index_lines = [
        "# Estado de tareas",
        "",
        "| ID | Tarea | Estado | Owner | Depende de |",
        "|---|---|---|---|---|",
    ]
    for row in markdown_table.parse_first_table(index_path.read_text(encoding="utf-8"))[1]:
        if len(row) == 5:
            tid, link, status, o, dep = row
            if tid == task_id:
                index_lines.append(f"| {tid} | [{link}](tasks/{link}) | `review` | — | {dep} |")
            else:
                index_lines.append(f"| {tid} | [{link}](tasks/{link}) | `{status}` | {o} | {dep} |")

    # Crear temporales
    temp_task = task_path.with_suffix(".md.tmp")
    temp_index = index_path.with_suffix(".md.tmp")

    try:
        temp_task.write_text(new_task_content, encoding="utf-8")
        temp_index.write_text("\n".join(index_lines) + "\n", encoding="utf-8")

        # Atomic replace
        shutil.move(str(temp_task), str(task_path))
        shutil.move(str(temp_index), str(index_path))
    except OSError as error:
        print(f"error escribiendo: {error}", file=sys.stderr)
        # Restaurar si falló
        if temp_task.exists():
            try:
                shutil.move(str(temp_task), str(task_path))
            except OSError:
                temp_task.unlink()
        if temp_index.exists():
            try:
                shutil.move(str(temp_index), str(index_path))
            except OSError:
                temp_index.unlink()
        # Restaurar originales si los temporales no se movieron
        if task_path.exists() and task_path.suffix == ".md.tmp":
            task_path.rename(task_path.with_suffix(".md"))
        if index_path.exists() and index_path.suffix == ".md.tmp":
            index_path.rename(index_path.with_suffix(".md"))
        return 2

    return 0


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada de la CLI."""
    parser = argparse.ArgumentParser(prog="taskctl", description="Validador y transiciones del tablero de tareas")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--root", default=".", help="Raíz del repositorio")
    claim_parser = subparsers.add_parser("claim")
    claim_parser.add_argument("task_id")
    claim_parser.add_argument("--owner", required=True)
    claim_parser.add_argument("--root", default=".", help="Raíz del repositorio")
    submit_parser = subparsers.add_parser("submit")
    submit_parser.add_argument("task_id")
    submit_parser.add_argument("--root", default=".", help="Raíz del repositorio")
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code)

    if args.command == "validate":
        return validate(args.root)

    if args.command == "claim":
        return claim_task(args.task_id, args.owner, args.root)

    if args.command == "submit":
        return submit_task(args.task_id, args.root)

if __name__ == "__main__":
    sys.exit(main())
