#!/usr/bin/env python3
"""Pruebas unitarias de monitoring/preflight.py.

La disponibilidad de binarios se inyecta con un ``which`` simulado para no
depender del hardware real (la máquina de desarrollo no tiene GPU).
"""
import contextlib
import io
import json
import subprocess
import unittest

from monitoring import preflight


ALL_TOOLS = {"systemctl", "nvidia-smi", "promtool", "systemd-analyze"}


def _ok_runner(command, **kwargs):
    """Runner simulado que hace exitoso cualquier binario externo."""
    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


def _which_factory(available):
    """Devuelve un ``which`` simulado limitado al conjunto ``available``."""
    def which(name):
        return f"/usr/bin/{name}" if name in available else None
    return which


class PreflightProfileTests(unittest.TestCase):
    """Comportamiento de los perfiles ``dev`` y ``server``."""

    def _run(self, argv, available, runner=None):
        kwargs = {"which": _which_factory(available)}
        if runner is not None:
            kwargs["runner"] = runner
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = preflight.main(argv, **kwargs)
        return code, output.getvalue()

    def test_dev_without_gpu_exits_zero(self):
        """En dev la ausencia de nvidia-smi es un WARNING no bloqueante."""
        code, output = self._run(["--profile", "dev"], {"systemctl"})
        self.assertEqual(code, 0)
        self.assertIn("nvidia-smi", output)
        self.assertIn("[WARNING]", output)

    def test_dev_with_gpu_exits_zero_and_all_ok(self):
        code, output = self._run(
            ["--profile", "dev"], {"systemctl", "nvidia-smi"}
        )
        self.assertEqual(code, 0)
        self.assertNotIn("[ERROR]", output)
        self.assertIn("[OK]", output)

    def test_server_without_gpu_exits_one(self):
        """En server la ausencia de nvidia-smi es bloqueante."""
        code, output = self._run(["--profile", "server"], {"systemctl"})
        self.assertEqual(code, 1)
        self.assertIn("[ERROR]", output)

    def test_server_with_gpu_exits_zero(self):
        code, _ = self._run(
            ["--profile", "server"], ALL_TOOLS, runner=_ok_runner
        )
        self.assertEqual(code, 0)

    def test_systemctl_is_always_mandatory(self):
        """Sin systemctl ni siquiera dev puede dar verde."""
        code, output = self._run(["--profile", "dev"], set())
        self.assertEqual(code, 1)
        self.assertIn("systemctl", output)

    def test_default_profile_is_strict(self):
        """La invocación sin argumentos conserva la semántica estricta."""
        parser = preflight.build_parser()
        self.assertEqual(parser.parse_args([]).profile, "server")


class PreflightJsonTests(unittest.TestCase):
    """El modo ``--json`` emite un informe estructurado por check."""

    def _run_json(self, argv, available, runner=None):
        kwargs = {"which": _which_factory(available)}
        if runner is not None:
            kwargs["runner"] = runner
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = preflight.main(argv, **kwargs)
        return code, json.loads(output.getvalue())

    def test_dev_json_is_valid_and_reports_each_check(self):
        code, payload = self._run_json(
            ["--profile", "dev", "--json"], {"systemctl"}
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["profile"], "dev")
        self.assertEqual(payload["exit_code"], 0)
        self.assertTrue(payload["ok"])
        statuses = {check["name"]: check["status"] for check in payload["checks"]}
        self.assertEqual(statuses["systemctl"], "ok")
        self.assertEqual(statuses["nvidia-smi"], "warning")
        for check in payload["checks"]:
            self.assertIn("message", check)
            self.assertIn("required", check)
            self.assertTrue(check["message"])

    def test_server_json_reports_blocking_error(self):
        code, payload = self._run_json(
            ["--profile", "server", "--json"], {"systemctl"}
        )
        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["exit_code"], 1)
        statuses = {check["name"]: check["status"] for check in payload["checks"]}
        self.assertEqual(statuses["nvidia-smi"], "error")
        nvidia = next(
            check for check in payload["checks"] if check["name"] == "nvidia-smi"
        )
        self.assertTrue(nvidia["required"])

    def test_server_json_all_ok(self):
        code, payload = self._run_json(
            ["--profile", "server", "--json"], ALL_TOOLS, runner=_ok_runner
        )
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        self.assertTrue(
            all(check["status"] == "ok" for check in payload["checks"])
        )


if __name__ == "__main__":
    unittest.main()
