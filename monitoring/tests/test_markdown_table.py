"""Tests unitarios para el parser de tablas Markdown."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from markdown_table import parse_first_table, TableFormatError


class TestParseFirstTable(unittest.TestCase):
    """Tests para parse_first_table."""

    def test_table_valid(self):
        """Tabla Markdown válida básica."""
        text = """
|| Campo | Valor |
||---|---|
|| Status | in_progress |
|| Owner | Hermes |
"""
        headers, rows = parse_first_table(text)
        self.assertEqual(headers, ['Campo', 'Valor'])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], ['Status', 'in_progress'])
        self.assertEqual(rows[1], ['Owner', 'Hermes'])

    def test_table_with_backticks(self):
        """Tabla con backticks en valores."""
        text = """
|| Campo | Valor |
||---|---|
|| Status | `in_progress` |
|| Owner | `monitoringworker` |
"""
        headers, rows = parse_first_table(text)
        self.assertEqual(headers, ['Campo', 'Valor'])
        self.assertEqual(rows[0], ['Status', '`in_progress`'])
        self.assertEqual(rows[1], ['Owner', '`monitoringworker`'])

    def test_table_with_colons_in_separator(self):
        """Separador con dos puntos (opcional)."""
        text = """
|| Campo | Valor |
||---:|---:|
|| Status | 42 |
|| Owner | 123 |
"""
        headers, rows = parse_first_table(text)
        self.assertEqual(headers, ['Campo', 'Valor'])
        self.assertEqual(rows[0], ['Status', '42'])
        self.assertEqual(rows[1], ['Owner', '123'])

    def test_table_with_extra_spaces(self):
        """Tabla con espacios extra (deben eliminarse)."""
        text = """
|| Campo | Valor |
|| --- | --- |
|| Status | in_progress |
|| Owner | Hermes |
"""
        headers, rows = parse_first_table(text)
        self.assertEqual(headers, ['Campo', 'Valor'])
        self.assertEqual(rows[0], ['Status', 'in_progress'])
        self.assertEqual(rows[1], ['Owner', 'Hermes'])

    def test_multiple_tables_returns_first(self):
        """Con múltiples tablas, devuelve la primera."""
        text = """
|| A | B |
||---|---|
|| 1 | 2 |

|| X | Y |
||---|---|
|| 3 | 4 |
"""
        headers, rows = parse_first_table(text)
        self.assertEqual(headers, ['A', 'B'])
        self.assertEqual(rows[0], ['1', '2'])

    def test_no_table_raises_error(self):
        """Sin tabla, lanza TableFormatError."""
        text = "Esto es solo texto sin tablas."
        with self.assertRaises(TableFormatError) as ctx:
            parse_first_table(text)
        self.assertIn("tabla", str(ctx.exception).lower())

    def test_empty_separator_raises_error(self):
        """Separador vacío lanza error."""
        text = """
|| A | B |
||   |   |
|| 1 | 2 |
"""
        with self.assertRaises(TableFormatError):
            parse_first_table(text)

    def test_no_data_raises_error(self):
        """Tabla sin datos lanza error."""
        text = """
|| A | B |
||---|---|
"""
        with self.assertRaises(TableFormatError) as ctx:
            parse_first_table(text)
        self.assertIn("datos", str(ctx.exception).lower())

    def test_inconsistent_columns_raises_error(self):
        """Columnas inconsistentes lanzan error."""
        text = """
|| A | B | C |
||---|---|---|
|| 1 | 2 |
"""
        with self.assertRaises(TableFormatError) as ctx:
            parse_first_table(text)
        self.assertIn("columnas", str(ctx.exception).lower())

    def test_invalid_separator_raises_error(self):
        """Separador inválido lanza error."""
        text = """
|| A | B |
||===|===|
|| 1 | 2 |
"""
        with self.assertRaises(TableFormatError):
            parse_first_table(text)

    def test_single_column_table(self):
        """Tabla de una columna."""
        text = """
|| A |
||---|
|| 1 |
|| 2 |
"""
        headers, rows = parse_first_table(text)
        self.assertEqual(headers, ['A'])
        self.assertEqual(rows[0], ['1'])
        self.assertEqual(rows[1], ['2'])

    def test_table_with_empty_cells(self):
        """Tabla con celdas vacías."""
        text = """
|| A | B |
||---|---|
|| 1 | |
|| | 2 |
"""
        headers, rows = parse_first_table(text)
        self.assertEqual(headers, ['A', 'B'])
        self.assertEqual(rows[0], ['1', ''])
        self.assertEqual(rows[1], ['', '2'])

    def test_table_with_unicode(self):
        """Tabla con caracteres unicode."""
        text = """
|| Nombre | Valor |
||---|---|
|| Café | ☕ |
|| Hola | 🌍 |
"""
        headers, rows = parse_first_table(text)
        self.assertEqual(headers, ['Nombre', 'Valor'])
        self.assertEqual(rows[0], ['Café', '☕'])
        self.assertEqual(rows[1], ['Hola', '🌍'])


if __name__ == '__main__':
    unittest.main()
