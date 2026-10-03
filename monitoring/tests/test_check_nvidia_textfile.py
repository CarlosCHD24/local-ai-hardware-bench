#!/usr/bin/env python3
"""Pruebas unitarias de monitoring/check_nvidia_textfile.py.

Los ``.prom`` se generan en ``tmp_path`` a partir de la definición real del
colector (``nvidia_metrics.METRICS``), por lo que no se duplican nombres.
"""
import contextlib
import io
import json
import os
import time

from monitoring import check_nvidia_textfile, nvidia_metrics, nvidia_textfile, preflight


def _content(success=1, skip=()):
    lines = []
    for name, _, _ in nvidia_metrics.METRICS:
        if name in skip:
            continue
        value = success if name == check_nvidia_textfile.SUCCESS_METRIC else 1
        lines.append(f'{name}{{gpu="0"}} {value}')
    return "\n".join(lines) + "\n"


def _write_prom(tmp_path, success=1, skip=(), name=None, age=0):
    path = tmp_path / (name or nvidia_textfile.NAME)
    path.write_text(_content(success=success, skip=skip), encoding="utf-8")
    if age:
        stamp = time.time() - age
        os.utime(path, (stamp, stamp))
    return path


def _which_factory(available):
    def which(name):
        return f"/usr/bin/{name}" if name in available else None
    return which


def test_metric_definitions_are_reused():
    assert check_nvidia_textfile.SUCCESS_METRIC in {
        name for name, _, _ in nvidia_metrics.METRICS
    }
    assert len(check_nvidia_textfile.GPU_METRICS) == 5
    assert check_nvidia_textfile.SUCCESS_METRIC not in check_nvidia_textfile.GPU_METRICS


def test_fresh_successful_textfile_exits_zero(tmp_path):
    _write_prom(tmp_path)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = check_nvidia_textfile.main(["--directory", str(tmp_path)])
    assert code == 0
    assert "textfile: 1 fichero(s) .prom" in output.getvalue()
    assert "scrape_success" in output.getvalue()


def test_old_textfile_exits_one(tmp_path):
    _write_prom(tmp_path, age=1000)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = check_nvidia_textfile.main(["--directory", str(tmp_path)])
    assert code == 1
    assert "frescura" in output.getvalue()


def test_scrape_success_zero_exits_one(tmp_path):
    _write_prom(tmp_path, success=0)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = check_nvidia_textfile.main(["--directory", str(tmp_path)])
    assert code == 1
    assert "se espera 1" in output.getvalue()


def test_missing_gpu_metric_exits_one(tmp_path):
    _write_prom(tmp_path, skip=(check_nvidia_textfile.GPU_METRICS[0],))
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = check_nvidia_textfile.main(["--directory", str(tmp_path)])
    assert code == 1
    assert "faltan" in output.getvalue()


def test_empty_directory_exits_one(tmp_path):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = check_nvidia_textfile.main(["--directory", str(tmp_path)])
    assert code == 1
    assert "sin ficheros .prom" in output.getvalue()


def test_json_is_valid_and_per_check(tmp_path):
    _write_prom(tmp_path)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = check_nvidia_textfile.main(
            ["--directory", str(tmp_path), "--json"]
        )
    assert code == 0
    payload = json.loads(output.getvalue())
    assert payload["exit_code"] == 0
    assert payload["ok"] is True
    names = {check["name"] for check in payload["checks"]}
    assert names == {
        "textfile-present",
        "textfile-fresh",
        "textfile-scrape-success",
        "textfile-gpu-metrics",
    }
    assert all(check["status"] == "ok" for check in payload["checks"])


def test_preflight_server_with_textfile_dir(tmp_path):
    _write_prom(tmp_path)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = preflight.main(
            [
                "--profile",
                "server",
                "--textfile-dir",
                str(tmp_path),
                "--json",
            ],
            which=_which_factory({"systemctl", "nvidia-smi"}),
            textfile_now=time.time(),
        )
    assert code == 0
    payload = json.loads(output.getvalue())
    statuses = {check["name"]: check["status"] for check in payload["checks"]}
    assert statuses["textfile-present"] == "ok"
    assert statuses["textfile-gpu-metrics"] == "ok"


def test_preflight_dev_without_textfile_dir_is_unchanged():
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = preflight.main(
            ["--profile", "dev"], which=_which_factory({"systemctl"})
        )
    assert code == 0
    assert "textfile" not in output.getvalue()
