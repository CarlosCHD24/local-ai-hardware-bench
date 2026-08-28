import io
import subprocess
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from monitoring import nvidia_metrics


QUERY = [
    "nvidia-smi",
    "--query-gpu=index,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,power.limit",
    "--format=csv,noheader,nounits",
]


def invoke(argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = nvidia_metrics.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


class NvidiaMetricsContract(unittest.TestCase):
    @mock.patch("monitoring.nvidia_metrics.subprocess.run")
    def test_one_gpu_and_exact_invocation(self, run):
        run.return_value = subprocess.CompletedProcess(
            QUERY, 0, "0, 25, 1024, 12288, 51, 120.5, 170\n", ""
        )
        code, stdout, stderr = invoke(["--timeout", "7"])
        self.assertEqual((code, stderr), (0, ""))
        self.assertIn('local_ai_gpu_utilization_ratio{gpu="0"} 0.25', stdout)
        self.assertIn('local_ai_gpu_memory_used_bytes{gpu="0"} 1073741824', stdout)
        self.assertIn('local_ai_gpu_scrape_success{gpu="0"} 1', stdout)
        args, kwargs = run.call_args
        self.assertEqual(args[0], QUERY)
        self.assertEqual(kwargs["timeout"], 7)
        self.assertFalse(kwargs.get("shell", False))

    @mock.patch("monitoring.nvidia_metrics.subprocess.run")
    def test_multiple_gpus_are_sorted(self, run):
        run.return_value = subprocess.CompletedProcess(
            QUERY,
            0,
            "2, 10, 10, 20, 40, 20, 30\n0, 20, 30, 40, 50, 40, 50\n",
            "",
        )
        code, stdout, _ = invoke([])
        self.assertEqual(code, 0)
        self.assertLess(stdout.index('gpu="0"'), stdout.index('gpu="2"'))

    @mock.patch("monitoring.nvidia_metrics.subprocess.run")
    def test_non_positive_timeout_does_not_run_process(self, run):
        code, _, _ = invoke(["--timeout", "0"])
        self.assertEqual(code, 2)
        run.assert_not_called()

    def test_execution_failures_emit_only_failure_metric(self):
        failures = (
            FileNotFoundError(),
            subprocess.TimeoutExpired(QUERY, 5),
            subprocess.CompletedProcess(QUERY, 1, "", "secret external error"),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                if isinstance(failure, subprocess.CompletedProcess):
                    patcher = mock.patch(
                        "monitoring.nvidia_metrics.subprocess.run", return_value=failure
                    )
                else:
                    patcher = mock.patch(
                        "monitoring.nvidia_metrics.subprocess.run", side_effect=failure
                    )
                with patcher:
                    code, stdout, stderr = invoke([])
                self.assertEqual(code, 3)
                self.assertEqual(stdout, "local_ai_gpu_scrape_success 0\n")
                self.assertNotIn("secret external error", stderr)

    @mock.patch("monitoring.nvidia_metrics.subprocess.run")
    def test_invalid_csv_never_emits_partial_metrics(self, run):
        invalid_rows = ("0, 10\n", "0, N/A, 1, 2, 3, 4, 5\n", "x, 1, 2, 3, 4, 5, 6\n")
        for body in invalid_rows:
            with self.subTest(body=body):
                run.return_value = subprocess.CompletedProcess(QUERY, 0, body, "")
                code, stdout, _ = invoke([])
                self.assertEqual(code, 3)
                self.assertEqual(stdout, "local_ai_gpu_scrape_success 0\n")


if __name__ == "__main__":
    unittest.main()
