#!/usr/bin/env python3
"""Pruebas unitarias de monitoring/check_listeners.py.

El contenido de ``/proc/net/tcp`` se sintetiza en un fichero temporal
(``tmp_path``) para no depender de los listeners reales del host.
"""
import contextlib
import io
import json

from monitoring import check_listeners, preflight

PROC_HEADER = (
    "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when "
    "retrnsmt   uid  timeout inode\n"
)
# 127.0.0.1:9100 en estado LISTEN (0A).
LISTEN_9100 = "   0: 0100007F:238C 00000000:0000 0A 00000000:00000000 00:00000000 00000000  1000 0 1\n"
# 127.0.0.1:9090 en estado LISTEN (0A).
LISTEN_9090 = "   1: 0100007F:2382 00000000:0000 0A 00000000:00000000 00:00000000 00000000  1000 0 2\n"
# 127.0.0.1:3000 en estado ESTABLISHED (01): no debe contar como listener.
ESTABLISHED_3000 = "   2: 0100007F:0BB8 00000000:0000 01 00000000:00000000 00:00000000 00000000  1000 0 3\n"
# 0.0.0.0:9100 en LISTEN: fuera de loopback.
WILDCARD_9100 = "   3: 00000000:238C 00000000:0000 0A 00000000:00000000 00:00000000 00000000  1000 0 4\n"


def _proc_text(*rows):
    return PROC_HEADER + "".join(rows)


def _write_proc(tmp_path, *rows):
    proc = tmp_path / "tcp"
    proc.write_text(_proc_text(*rows), encoding="utf-8")
    return proc


def _which_factory(available):
    def which(name):
        return f"/usr/bin/{name}" if name in available else None
    return which


def test_parse_proc_net_tcp_detects_only_listen_entries():
    text = _proc_text(LISTEN_9100, LISTEN_9090, ESTABLISHED_3000, WILDCARD_9100)
    listeners = check_listeners.parse_proc_net_tcp(text)
    assert listeners == {
        "127.0.0.1:9100",
        "127.0.0.1:9090",
        "0.0.0.0:9100",
    }
    assert "127.0.0.1:3000" not in listeners


def test_wildcard_bind_does_not_satisfy_loopback(tmp_path):
    proc = _write_proc(tmp_path, WILDCARD_9100)
    assert check_listeners.main(
        ["--require", "127.0.0.1:9100", "--proc", str(proc)]
    ) == 1


def test_list_listeners_reads_file(tmp_path):
    proc = _write_proc(tmp_path, LISTEN_9100)
    assert check_listeners.list_listeners(proc) == {"127.0.0.1:9100"}


def test_parse_requirements_trims_and_normalizes():
    spec = "127.0.0.1:9100, 127.0.0.1:09090, "
    assert check_listeners.parse_requirements(spec) == [
        "127.0.0.1:9100",
        "127.0.0.1:9090",
    ]


def test_present_listener_exits_zero(tmp_path):
    proc = _write_proc(tmp_path, LISTEN_9100)
    code = check_listeners.main(
        ["--require", "127.0.0.1:9100", "--proc", str(proc)]
    )
    assert code == 0


def test_missing_listener_exits_one_and_reports(tmp_path):
    proc = _write_proc(tmp_path, LISTEN_9100)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = check_listeners.main(
            ["--require", "127.0.0.1:9100,127.0.0.1:9090", "--proc", str(proc)]
        )
    assert code == 1
    text = output.getvalue()
    assert "listener 127.0.0.1:9100: presente" in text
    assert "listener 127.0.0.1:9090: falta" in text


def test_json_output_is_valid_and_per_listener(tmp_path):
    proc = _write_proc(tmp_path, LISTEN_9100)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = check_listeners.main(
            [
                "--require",
                "127.0.0.1:9100,127.0.0.1:9090",
                "--proc",
                str(proc),
                "--json",
            ]
        )
    assert code == 1
    payload = json.loads(output.getvalue())
    assert payload["exit_code"] == 1
    assert payload["ok"] is False
    by_name = {item["name"]: item for item in payload["listeners"]}
    assert by_name["listener:127.0.0.1:9100"]["status"] == "ok"
    assert by_name["listener:127.0.0.1:9090"]["status"] == "error"
    assert by_name["listener:127.0.0.1:9090"]["present"] is False


def test_preflight_includes_listener_checks_in_json(tmp_path):
    proc = _write_proc(tmp_path, LISTEN_9100)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = preflight.main(
            [
                "--profile",
                "dev",
                "--require-listeners",
                "127.0.0.1:9100,127.0.0.1:9090",
                "--json",
            ],
            which=_which_factory({"systemctl"}),
            proc_path=proc,
        )
    assert code == 1
    payload = json.loads(output.getvalue())
    statuses = {check["name"]: check["status"] for check in payload["checks"]}
    assert statuses["listener:127.0.0.1:9100"] == "ok"
    assert statuses["listener:127.0.0.1:9090"] == "error"


def test_preflight_without_require_listeners_is_unchanged(tmp_path):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = preflight.main(
            ["--profile", "dev"],
            which=_which_factory({"systemctl"}),
        )
    assert code == 0
    assert "listener" not in output.getvalue()
