import unittest

from monitoring import markdown_table


class MarkdownTableContract(unittest.TestCase):
    def test_valid_single_pipe_table(self):
        text = """# Documento

Texto previo.

| Campo | Valor |
|---|:---:|
| Status | `ready` |
| Owner | — |
"""
        header, rows = markdown_table.parse_first_table(text)
        self.assertEqual(header, ["Campo", "Valor"])
        self.assertEqual(rows, [["Status", "`ready`"], ["Owner", "—"]])

    def test_preserves_content_and_stops_at_first_table(self):
        text = """| A | B |
|---|---|
|  x  | `y` |

| C | D |
|---|---|
| ignored | ignored |
"""
        header, rows = markdown_table.parse_first_table(text)
        self.assertEqual(header, ["A", "B"])
        self.assertEqual(rows, [["x", "`y`"]])

    def test_double_pipe_is_rejected(self):
        with self.assertRaises(markdown_table.TableFormatError):
            markdown_table.parse_first_table(
                "|| Campo | Valor ||\n||---|---||\n|| Status | `ready` ||\n"
            )

    def test_separator_and_column_count_are_validated(self):
        invalid = (
            "| A | B |\n|--|---|\n| x | y |\n",
            "| A | B |\n|---|---|\n| x |\n",
        )
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(
                markdown_table.TableFormatError
            ):
                markdown_table.parse_first_table(text)

    def test_missing_table_or_data_is_rejected(self):
        for text in ("sin tabla", "| A | B |\n|---|---|\n"):
            with self.subTest(text=text), self.assertRaises(
                markdown_table.TableFormatError
            ):
                markdown_table.parse_first_table(text)


if __name__ == "__main__":
    unittest.main()
