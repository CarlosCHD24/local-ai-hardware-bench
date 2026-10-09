"""Validador de sólo lectura del tablero de tareas."""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from monitoring import markdown_table


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


def utc_now() -> str:
    """Devuelve la hora UTC en el formato del tablero."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _task_path(tasks_dir: Path, task_id: str) -> Path | None:
    """Localiza la única tarea cuyo nombre comienza por su identificador."""
    paths = sorted(tasks_dir.glob(f"{task_id}-*.md"))
    return paths[0] if len(paths) == 1 else None


def _replace_metadata(text: str, *, status: str, owner: str, updated: str) -> str:
    """Actualiza sólo los tres metadatos que pertenecen a una transición."""
    replacements = {
        "Status": f"`{status}`",
        "Owner": owner,
        "Updated": updated,
    }
    for field, value in replacements.items():
        pattern = rf"^(\|\s*{re.escape(field)}\s*\|).*?(\|\s*)$"
        text, count = re.subn(pattern, rf"\1 {value} \2", text, flags=re.MULTILINE)
        if count != 1:
            raise ValueError(f"campo de tarea no actualizable: {field}")
    return text


def _replace_index_row(text: str, task_id: str, *, status: str, owner: str) -> str:
    """Actualiza el estado y owner de una fila sin reescribir el tablero."""
    lines = text.splitlines(keepends=True)
    matches = [index for index, line in enumerate(lines) if line.lstrip().startswith(f"| {task_id} |")]
    if len(matches) != 1:
        raise ValueError(f"fila de índice no actualizable: {task_id}")
    index = matches[0]
    line = lines[index]
    newline = "\n" if line.endswith("\n") else ""
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if len(cells) != 5 or cells[0] != task_id:
        raise ValueError(f"fila de índice inválida: {task_id}")
    cells[2] = f"`{status}`"
    cells[3] = owner
    lines[index] = "| " + " | ".join(cells) + " |" + newline
    return "".join(lines)


def _atomic_replace(task_path: Path, task_text: str, index_path: Path, index_text: str) -> bool:
    """Sustituye ambos documentos o restaura el primero si falla el segundo."""
    originals = (task_path.read_bytes(), index_path.read_bytes())
    task_temp = task_path.with_name(f".{task_path.name}.tmp")
    index_temp = index_path.with_name(f".{index_path.name}.tmp")
    task_temp.write_text(task_text, encoding="utf-8")
    index_temp.write_text(index_text, encoding="utf-8")
    try:
        os.replace(task_temp, task_path)
        try:
            os.replace(index_temp, index_path)
        except OSError:
            rollback = task_path.with_name(f".{task_path.name}.rollback")
            rollback.write_bytes(originals[0])
            os.replace(rollback, task_path)
            return False
    except OSError:
        return False
    finally:
        for temporary in (task_temp, index_temp, task_path.with_name(f".{task_path.name}.rollback")):
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    return True


def _transition(task_id: str, root: Path, *, expected: str, status: str, owner: str) -> int:
    """Aplica una transición de tarea tras validar el tablero antes y después."""
    root = Path(root)
    before_code, _, _ = validate(root)
    if before_code != 0:
        return 2 if before_code == 2 else 1
    tasks_dir = root / "monitoring" / "building" / "tasks"
    index_path = root / "monitoring" / "building" / "TASKS.md"
    task_path = _task_path(tasks_dir, task_id)
    if task_path is None:
        return 1
    metadata = parse_task_file(task_path)
    if unquote(metadata.get("Status", "")) != expected:
        return 1
    if expected == "ready":
        if not owner or owner == "—":
            return 1
        dependency = unquote(metadata.get("Depends on", ""))
        if dependency not in ("", "—"):
            dependency_path = _task_path(tasks_dir, dependency)
            if dependency_path is None or unquote(parse_task_file(dependency_path).get("Status", "")) != "done":
                return 1
    elif metadata.get("Owner", "") in ("", "—"):
        return 1
    task_original = task_path.read_text(encoding="utf-8")
    index_original = index_path.read_text(encoding="utf-8")
    try:
        task_updated = _replace_metadata(task_original, status=status, owner=owner, updated=utc_now())
        index_updated = _replace_index_row(index_original, task_id, status=status, owner=owner)
    except ValueError:
        return 2
    if not _atomic_replace(task_path, task_updated, index_path, index_updated):
        return 2
    after_code, _, _ = validate(root)
    if after_code == 0:
        return 0
    _atomic_replace(task_path, task_original, index_path, index_original)
    return 2


def claim_task(task_id: str, owner: str, root: Path) -> int:
    """Reclama una tarea ready cuyas dependencias ya están terminadas."""
    return _transition(task_id, root, expected="ready", status="in_progress", owner=owner)


def submit_task(task_id: str, root: Path) -> int:
    """Envía una tarea reclamada a revisión y libera su owner."""
    return _transition(task_id, root, expected="in_progress", status="review", owner="—")


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
    args = parser.parse_args(argv)
    if args.command == "validate":
        code, errors, count = validate(Path(args.root))
        if code == 0:
            print(f"OK: {count} tasks")
        else:
            for error in errors:
                print(error, file=sys.stderr)
        return code
    if args.command == "claim":
        return claim_task(args.task_id, args.owner, Path(args.root))
    return submit_task(args.task_id, Path(args.root))


if __name__ == "__main__":
    sys.exit(main())
