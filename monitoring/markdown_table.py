"""Parser de tablas Markdown estándar."""

import re


class TableFormatError(ValueError):
    """Error de formato de tabla Markdown."""
    pass


def parse_first_table(text: str) -> tuple[list[str], list[list[str]]]:
    """
    Parsea la primera tabla Markdown estándar del texto.

    Devuelve (cabeceras, filas) sin la línea separadora.
    Elimina espacios exteriores de celdas, conserva backticks y texto.

    Exige al menos una fila de datos, mismo número de columnas en todas las filas,
    y separadores `---` con dos puntos opcionales. Una línea vacía o no tabular
    termina la tabla.

    Cada celda separadora se valida con el patrón equivalente a `^:?-{3,}:?$`.
    `:---:`, `---` y `-----` son válidos.

    Lanza TableFormatError si no hay tabla, separador inválido, sin datos,
    o filas con distinto número de columnas.
    """
    lines = text.splitlines()

    # Buscar la primera línea de cabecera de tabla (empieza con | y tiene al menos 3 columnas)
    header_line_idx = None
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        # Línea de cabecera: empieza con |, tiene al menos 3 columnas (2 pipes internos)
        stripped = line.strip()
        if stripped.startswith('|') and stripped.count('|') >= 3:
            header_line_idx = i
            break

    if header_line_idx is None:
        raise TableFormatError("No se encontró una cabecera de tabla válida")

    # Línea de separador (debe estar justo después de la cabecera)
    separator_line_idx = header_line_idx + 1
    if separator_line_idx >= len(lines):
        raise TableFormatError("Falta la línea de separador de tabla")

    separator = lines[separator_line_idx].strip()

    # Eliminar pipes del separador para validar el contenido
    separator_content = separator.replace('|', '')

    # Validar separador: debe ser solo guiones con dos puntos opcionales
    # Patrón: ^:?-{3,}:?$ permite ---, :---, ---:, :---:
    if not re.match(r'^:?-{3,}:?$', separator_content):
        raise TableFormatError(f"Separador de tabla inválido: {separator!r}")

    # Extraer cabeceras
    header_cells = _parse_cells(lines[header_line_idx])
    num_columns = len(header_cells)
    if num_columns < 2:
        raise TableFormatError("La tabla debe tener al menos 2 columnas")

    # Contar bloques de separador: el separador original debe tener la forma |bloque1|bloque2|...|
    # Ej: |---|:---:| → bloques son "---" y ":---:" → 2 bloques
    # Contamos los bloques separando por '|' y filtrando espacios vacíos
    separator_blocks = re.split(r'\|', separator)
    separator_blocks = [b.strip() for b in separator_blocks if b.strip()]
    if len(separator_blocks) != num_columns:
        raise TableFormatError(f"Separador de tabla inválido: número de bloques ({len(separator_blocks)}) != columnas ({num_columns})")

    # Extraer filas de datos (hasta encontrar línea vacía o no tabular)
    rows = []
    for i in range(separator_line_idx + 1, len(lines)):
        line = lines[i].strip()

        # Línea vacía o no tabular termina la tabla
        if not line or not line.startswith('|'):
            break

        cells = _parse_cells(line)

        # Validar número de columnas
        if len(cells) != num_columns:
            raise TableFormatError(
                f"Fila con número incorrecto de columnas: {len(cells)} en lugar de {num_columns}"
            )

        # Validar que no sea una línea de separador (ya que no debería aparecer)
        if re.match(r'^:?-{3,}:?$', line.replace('|', '')):
            break

        rows.append(cells)

    # Exigir al menos una fila de datos
    if not rows:
        raise TableFormatError("La tabla debe tener al menos una fila de datos")

    return header_cells, rows


def _parse_cells(line: str) -> list[str]:
    """
    Extrae celdas de una línea de tabla Markdown.

    Elimina espacios exteriores de cada celda, conserva backticks y texto.
    Rechaza líneas con doble pipe (||) que indican celdas vacías no permitidas.
    """
    # Eliminar pipes de los extremos
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]

    # Dividir por pipes
    cells = [cell.strip() for cell in line.split('|')]

    # Validar que no haya doble pipe (||) en la línea original
    # Esto ocurre cuando hay celdas vacías entre pipes consecutivos
    if '||' in line:
        raise TableFormatError("Formato de tabla inválido: celdas vacías no permitidas")

    return cells
