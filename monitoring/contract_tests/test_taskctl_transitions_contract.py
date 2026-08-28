import tempfile
import unittest
from pathlib import Path
from unittest import mock

from monitoring import taskctl
from monitoring.contract_tests.test_taskctl_contract import invoke, write_index, write_task


class TaskctlTransitionsContract(unittest.TestCase):
    def make_project(self, root, *, dependency_status="done", task_status="ready"):
        write_task(root, "TASK-001", "base", status=dependency_status)
        owner = "Hermes" if task_status == "in_progress" else "—"
        write_task(
            root,
            "TASK-002",
            "next",
            status=task_status,
            owner=owner,
            depends="TASK-001",
        )
        write_index(
            root,
            [
                ("TASK-001", "base", dependency_status, "—", "—"),
                ("TASK-002", "next", task_status, owner, "TASK-001"),
            ],
        )

    def test_claim_updates_both_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_project(root)
            with mock.patch(
                "monitoring.taskctl.utc_now", return_value="2026-08-29T00:00:00Z"
            ):
                code, _, stderr = invoke(
                    ["claim", "TASK-002", "--owner", "Hermes", "--root", str(root)]
                )
            self.assertEqual((code, stderr), (0, ""))
            task_text = (root / "monitoring/building/tasks/TASK-002-next.md").read_text()
            index_text = (root / "monitoring/building/TASKS.md").read_text()
            self.assertIn("| Status | `in_progress` |", task_text)
            self.assertIn("| Owner | Hermes |", task_text)
            self.assertIn("2026-08-29T00:00:00Z", task_text)
            self.assertIn("| `in_progress` | Hermes |", index_text)
            self.assertEqual(invoke(["validate", "--root", str(root)])[0], 0)

    def test_claim_rejects_pending_dependency_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_project(root, dependency_status="ready")
            task = root / "monitoring/building/tasks/TASK-002-next.md"
            index = root / "monitoring/building/TASKS.md"
            before = (task.read_bytes(), index.read_bytes())
            code, _, _ = invoke(
                ["claim", "TASK-002", "--owner", "Hermes", "--root", str(root)]
            )
            self.assertEqual(code, 1)
            self.assertEqual((task.read_bytes(), index.read_bytes()), before)

    def test_submit_updates_both_documents_and_clears_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_project(root, task_status="in_progress")
            with mock.patch(
                "monitoring.taskctl.utc_now", return_value="2026-08-29T00:01:00Z"
            ):
                code, _, stderr = invoke(["submit", "TASK-002", "--root", str(root)])
            self.assertEqual((code, stderr), (0, ""))
            task_text = (root / "monitoring/building/tasks/TASK-002-next.md").read_text()
            index_text = (root / "monitoring/building/TASKS.md").read_text()
            self.assertIn("| Status | `review` |", task_text)
            self.assertIn("| Owner | — |", task_text)
            self.assertIn("| `review` | — |", index_text)

    def test_second_replace_failure_restores_originals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_project(root)
            task = root / "monitoring/building/tasks/TASK-002-next.md"
            index = root / "monitoring/building/TASKS.md"
            before = (task.read_bytes(), index.read_bytes())
            real_replace = taskctl.os.replace
            calls = 0

            def fail_second(source, destination):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated")
                return real_replace(source, destination)

            with mock.patch("monitoring.taskctl.os.replace", side_effect=fail_second):
                code, _, _ = invoke(
                    ["claim", "TASK-002", "--owner", "Hermes", "--root", str(root)]
                )
            self.assertEqual(code, 2)
            self.assertEqual((task.read_bytes(), index.read_bytes()), before)

    def test_done_is_not_a_subcommand(self):
        with self.assertRaises(SystemExit):
            taskctl.main(["done", "TASK-002", "--root", "."])


if __name__ == "__main__":
    unittest.main()
