"""Parser de tablas Markdown estándar."""

import re
from typing import List, Tuple


class TableFormatError(ValueError):
    """Error de formato de tabla Markdown."""
    pass


def parse_first_table(text: str) -> Tuple[List[str], List[List[str]]]:
    """
    Parsea la primera tabla Markdown estándar del texto.

    Args:
        text: Texto que puede contener una tabla Markdown.

    Returns:
        Tupla con (headers, rows) donde headers y rows son listas de listas de strings.

    Raises:
        TableFormatError: Si no hay tabla, formato inválido, o datos incompletos.
    """
    lines = text.split('\n')

    # Buscar la primera tabla
    table_start = None
    for i, line in enumerate(lines):
        if _is_separator_line(line):
            table_start = i
            break

    if table_start is None:
        raise TableFormatError("No se encontró ninguna tabla Markdown")

    # Extraer filas de la tabla (sin el separador)
    table_lines = []
    for i in range(table_start + 1, len(lines)):
        line = lines[i].strip()
        if not line or not _is_table_row(line):
            break
        table_lines.append(line)

    if len(table_lines) < 1:
        raise TableFormatError("La tabla debe tener al menos una fila de datos")

    # Parsear cabeceras
    headers = _parse_row(table_lines[0])

    # Parsear filas de datos
    rows = []
    for row_line in table_lines[1:]:
        row = _parse_row(row_line)
        rows.append(row)

    # Validar número de columnas consistente
    expected_cols = len(headers)
    for row in rows:
        if len(row) != expected_cols:
            raise TableFormatError(f"Inconsistencia de columnas: cabecera tiene {expected_cols}, fila tiene {len(row)}")

    return headers, rows


def _is_separator_line(line: str) -> bool:
    """Verifica si una línea es un separador de tabla válido."""
    stripped = line.strip()
    if not stripped:
        return False

    # Debe tener al menos 2 pipes (para 2 columnas mínimas)
    pipe_count = stripped.count('|')
    if pipe_count < 2:
        return False

    # El separador debe tener al menos un pipe al inicio y al final
    if not stripped.startswith('|') or not stripped.endswith('|'):
        return False

    # Eliminar pipes iniciales y finales consecutivos
    while stripped.startswith('|'):
        stripped = stripped[1:]
    while stripped.endswith('|'):
        stripped = stripped[:-1]

    if not stripped:
        return False

    # Dividir por pipes
    cells = stripped.split('|')

    # Validar cada celda del separador
    for cell in cells:
        if not re.match(r'^:?-{3,}:?$', cell):
            return False

    return True


def _is_table_row(line: str) -> bool:
    """Verifica si una línea es una fila de tabla válida."""
    stripped = line.strip()
    if not stripped:
        return False
    # Debe tener al menos 2 pipes (para 2 columnas mínimas)
    # Formatos válidos: | A | B | o || A | B ||
    pipe_count = stripped.count('|')
    # Una fila válida debe tener al menos 2 pipes
    return pipe_count >= 2


def _parse_row(line: str) -> List[str]:
    """
    Parsea una fila de tabla en una lista de celdas.

    Elimina espacios exteriores de cada celda.
    """
    # Debe tener al menos 2 pipes (para 2 columnas mínimas)
    stripped = line.strip()
    if not stripped:
        return []

    pipe_count = stripped.count('|')
    if pipe_count < 2:
        return []

    # El parse debe tener al menos un pipe al inicio y al final
    if not stripped.startswith('|') or not stripped.endswith('|'):
        return []

    # Eliminar espacios exteriores
    line = line.strip()

    # Eliminar pipes iniciales y finales consecutivos
    while line.startswith('|'):
        line = line[1:]
    while line.endswith('|'):
        line = line[:-1]

    if not line:
        return []

    # Dividir por pipes
    cells = line.split('|')

    # Eliminar espacios exteriores de cada celda
    cells = [cell.strip() for cell in cells]

    return cells
