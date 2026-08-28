"""Parser de tablas Markdown estándar (formato con doble pipe)."""

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
        Tupla con (cabeceras, filas) donde:
        - cabeceras: lista de strings con los nombres de columnas
        - filas: lista de listas de strings con los datos

    Raises:
        TableFormatError: Si no hay tabla, formato inválido, separador incorrecto,
                         sin datos, o columnas inconsistentes.
    """
    lines = text.split('\n')

    # Buscar la primera tabla
    table_start = None
    for i, line in enumerate(lines):
        if _is_table_row(line):
            table_start = i
            break

    if table_start is None:
        raise TableFormatError("No se encontró ninguna tabla Markdown")

    # Buscar el separador de tabla
    separator_line = None
    for i in range(table_start + 1, len(lines)):
        if _is_table_separator_line(lines[i]):
            separator_line = i
            break

    if separator_line is None:
        raise TableFormatError("No se encontró separador de tabla (---)")

    # Buscar fin de tabla (línea vacía o no tabular)
    table_end = separator_line + 1
    while table_end < len(lines):
        line = lines[table_end]
        if line.strip() == '' or (not _is_table_row(line) and '|' not in line):
            break
        table_end += 1

    # Extraer filas (sin la línea separadora)
    rows = []
    for i in range(table_start + 1, table_end):
        if _is_table_separator_line(lines[i]):
            continue
        row = _parse_table_row(lines[i])
        rows.append(row)

    if len(rows) == 0:
        raise TableFormatError("La tabla no tiene datos")

    # Verificar consistencia de columnas
    header_cols = _parse_table_row(lines[table_start])
    for i, row in enumerate(rows):
        if len(row) != len(header_cols) and len(header_cols) > 0:
            raise TableFormatError(
                f"Fila {i + 1} tiene {len(row)} columnas, "
                f"esperadas {len(header_cols)}"
            )

    return header_cols, rows


def _is_table_row(line: str) -> bool:
    """Verifica si una línea es una fila de tabla Markdown."""
    stripped = line.strip()
    if stripped == '' or '|' not in stripped:
        return False
    parts = stripped.split('|')
    # Formato válido: doble pipe al inicio y fin (|| ... ||)
    # O formato simple: al menos un pipe
    if stripped.startswith('|') and stripped.endswith('|'):
        return len(parts) >= 2
    return False


def _is_table_separator_line(line: str) -> bool:
    """Verifica si una línea es el separador de tabla Markdown."""
    stripped = line.strip()
    if stripped == '' or '|' not in stripped:
        return False
    parts = stripped.split('|')
    if len(parts) < 2:
        return False
    # Validar que todas las celdas tengan guiones (con o sin colones) de la misma longitud
    cells = [p.strip() for p in parts[1:-1]]
    if len(cells) == 0:
        return False
    first_len = len(cells[0])
    for cell in cells:
        # Validar que la celda contenga guiones (con o sin colones al inicio/fin)
        if '-' not in cell:
            return False
        if len(cell) != first_len:
            return False
    return True


def _parse_table_row(line: str) -> List[str]:
    """
    Parsea una fila de tabla Markdown en una lista de strings.

    Parsea formato || celda || eliminando espacios exteriores.
    """
    parts = line.split('|')
    cells = []
    for part in parts[1:-1]:
        cell = part.strip()
        cells.append(cell)
    return cells
