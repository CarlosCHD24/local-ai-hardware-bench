#!/usr/bin/env python3
"""Pruebas de la integración de validadores y binarios externos en preflight.

Simulan ``shutil.which`` y el runner de ``subprocess.run`` para no depender de
que ``promtool`` o ``systemd-analyze`` existan en la máquina de desarrollo.
"""
import contextlib
import io
import json
import subprocess

import pytest

from monitoring import preflight


def _which(available):
    def which(name):
        return f"/usr/bin/{name}" if name in available else None
    return which


def _runner(returncode=0, stderr=""):
    def run(command, **kwargs):
        return subprocess.CompletedProcess(
            command, returncode, stdout="", stderr=stderr
        )
    return run


def _unexpected(command, **kwargs):
    raise AssertionError("el runner no debe invocarse sin binario externo")


def _run(argv, available, runner):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = preflight.main(argv, which=_which(available), runner=runner)
    return code, output.getvalue()


def test_validators_are_included_and_ok():
    code, output = _run(["--profile", "dev", "--json"], {"systemctl"}, _unexpected)
    assert code == 0
    payload = json.loads(output)
    checks = {check["name"]: check for check in payload["checks"]}
    assert checks["validate_prometheus"]["status"] == "ok"
    assert checks["validate_operation"]["status"] == "ok"
    assert "tool" not in checks["validate_prometheus"]


def test_dev_missing_tools_are_warnings_exit_zero():
    code, output = _run(["--profile", "dev"], {"systemctl"}, _unexpected)
    assert code == 0
    assert "promtool: no encontrado en PATH" in output
    assert "systemd-analyze: no encontrado en PATH" in output
    assert output.count("[WARNING]") >= 2


def test_server_missing_tools_are_errors_exit_one():
    code, output = _run(
        ["--profile", "server"], {"systemctl", "nvidia-smi"}, _unexpected
    )
    assert code == 1
    assert "promtool: no encontrado en PATH" in output
    assert "systemd-analyze: no encontrado en PATH" in output


@pytest.mark.parametrize("profile", ["dev", "server"])
def test_promtool_present_and_failing_blocks_both_profiles(profile):
    code, output = _run(
        ["--profile", profile],
        {"systemctl", "nvidia-smi", "promtool"},
        _runner(returncode=1, stderr="bad config"),
    )
    assert code == 1
    assert "promtool: fallo (exit 1)" in output


def test_systemd_analyze_failure_is_warning_in_dev():
    code, output = _run(
        ["--profile", "dev"],
        {"systemctl", "nvidia-smi", "systemd-analyze"},
        _runner(returncode=1, stderr="unit error"),
    )
    assert code == 0
    assert "systemd-analyze: fallo (exit 1)" in output


def test_systemd_analyze_failure_is_error_in_server():
    code, _ = _run(
        ["--profile", "server"],
        {"systemctl", "nvidia-smi", "systemd-analyze"},
        _runner(returncode=1, stderr="unit error"),
    )
    assert code == 1


def test_tools_present_and_ok_exit_zero():
    code, _ = _run(
        ["--profile", "dev"],
        {"systemctl", "nvidia-smi", "promtool", "systemd-analyze"},
        _runner(returncode=0),
    )
    assert code == 0


def test_json_reports_tool_key_only_for_external_checks():
    code, output = _run(["--profile", "dev", "--json"], {"systemctl"}, _unexpected)
    assert code == 0
    checks = {check["name"]: check for check in json.loads(output)["checks"]}
    assert checks["promtool"]["tool"] == "promtool"
    assert checks["promtool"]["status"] == "warning"
    assert checks["systemd-analyze"]["tool"] == "systemd-analyze"
    assert "tool" not in checks["systemctl"]
    assert "tool" not in checks["validate_operation"]


def test_external_tools_receive_expected_arguments():
    calls = []

    def recording(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    code, _ = _run(
        ["--profile", "dev"],
        {"systemctl", "nvidia-smi", "promtool", "systemd-analyze"},
        recording,
    )
    assert code == 0
    invocations = {command[0].rsplit("/", 1)[-1]: command for command in calls}
    assert invocations["promtool"][1:3] == ["check", "config"]
    assert invocations["promtool"][3].endswith("prometheus.yml")
    assert invocations["systemd-analyze"][1] == "verify"
    assert any(arg.endswith(".timer") for arg in invocations["systemd-analyze"])
