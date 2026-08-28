import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from monitoring import taskctl


def write_task(
    root,
    task_id,
    slug,
    *,
    status="ready",
    owner="—",
    depends="—",
    updated="2026-08-28T22:52:58Z",
):
    path = root / "monitoring" / "building" / "tasks" / f"{task_id}-{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""# {task_id}: {slug}

| Campo | Valor |
|---|---|
| Status | `{status}` |
| Owner | {owner} |
| Created | 2026-08-28T22:52:58Z |
| Updated | {updated} |
| Depends on | {depends} |
| Execution | `orchestrated` |
| Profile | `monitoringworker` |
| Budget | 12 turns / 600 s / 2048 output / reasoning none |
| Rounds | 3 |
| Contract tests | `monitoring.contract_tests.example` |
| Working directory | Repository root |
""",
        encoding="utf-8",
    )
    return path


def write_index(root, rows):
    path = root / "monitoring" / "building" / "TASKS.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Estado de tareas",
        "",
        "| ID | Tarea | Estado | Owner | Depende de |",
        "|---|---|---|---|---|",
    ]
    for task_id, slug, status, owner, depends in rows:
        lines.append(
            f"| {task_id} | [{slug}](tasks/{task_id}-{slug}.md) | "
            f"`{status}` | {owner} | {depends} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def invoke(argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = taskctl.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


class TaskctlContract(unittest.TestCase):
    def test_valid_repository_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_task(root, "TASK-001", "base", status="done")
            write_task(root, "TASK-002", "next", depends="TASK-001")
            write_index(
                root,
                [
                    ("TASK-001", "base", "done", "—", "—"),
                    ("TASK-002", "next", "ready", "—", "TASK-001"),
                ],
            )
            code, stdout, stderr = invoke(["validate", "--root", str(root)])
            self.assertEqual((code, stderr), (0, ""))
            self.assertIn("OK: 2 tasks", stdout)

    def test_double_pipe_metadata_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task = write_task(root, "TASK-001", "base", status="done")
            task.write_text(
                task.read_text(encoding="utf-8").replace(
                    "| Campo | Valor |", "|| Campo | Valor ||"
                ),
                encoding="utf-8",
            )
            write_index(root, [("TASK-001", "base", "done", "—", "—")])
            code, _, stderr = invoke(["validate", "--root", str(root)])
            self.assertEqual(code, 1)
            self.assertIn("tabla", stderr.lower())

    def test_state_owner_and_timestamp_are_validated(self):
        cases = (
            {"status": "unknown"},
            {"status": "done", "owner": "Hermes"},
            {"updated": "2026-08-28 22:52:58"},
        )
        for changes in cases:
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                write_task(root, "TASK-001", "base", **changes)
                write_index(
                    root,
                    [("TASK-001", "base", changes.get("status", "ready"),
                      changes.get("owner", "—"), "—")],
                )
                code, _, _ = invoke(["validate", "--root", str(root)])
                self.assertEqual(code, 1)

    def test_missing_and_self_dependency_are_invalid(self):
        for dependency in ("TASK-999", "TASK-001"):
            with self.subTest(dependency=dependency), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                write_task(root, "TASK-001", "base", depends=dependency)
                write_index(
                    root,
                    [("TASK-001", "base", "ready", "—", dependency)],
                )
                code, _, stderr = invoke(["validate", "--root", str(root)])
                self.assertEqual(code, 1)
                self.assertIn("depend", stderr.lower())

    def test_index_state_and_link_are_compared(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_task(root, "TASK-001", "base", status="done")
            index = write_index(root, [("TASK-001", "base", "ready", "—", "—")])
            text = index.read_text(encoding="utf-8").replace(
                "tasks/TASK-001-base.md", "tasks/TASK-001-other.md"
            )
            index.write_text(text, encoding="utf-8")
            code, _, stderr = invoke(["validate", "--root", str(root)])
            self.assertEqual(code, 1)
            self.assertIn("TASK-001", stderr)

    def test_invalid_root_or_structure_returns_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "missing"
            self.assertEqual(invoke(["validate", "--root", str(missing)])[0], 2)
            self.assertEqual(invoke(["validate", "--root", str(root)])[0], 2)


if __name__ == "__main__":
    unittest.main()
