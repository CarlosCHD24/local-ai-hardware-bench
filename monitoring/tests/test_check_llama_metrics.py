#!/usr/bin/env python3
"""Pruebas unitarias para check_llama_metrics."""

import os
import sys
import tempfile
import unittest
import urllib.error
from io import StringIO
from unittest import mock

from monitoring import check_llama_metrics


class FakeResponse:
    """Simulación de respuesta HTTP."""
    def __init__(self, body, status=200):
        self.body, self.status = body.encode(), status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


class TestCheckLlamaMetrics(unittest.TestCase):
    """Pruebas para check_llama_metrics."""

    def setUp(self):
        """Preparar entorno de prueba."""
        self.base_url = "http://127.0.0.1:8080"
        self.timeout = 7

    def test_success_returns_0_and_accepts_labels(self):
        """Health válido y las 10 métricas, incluyendo una con etiquetas, devuelven 0."""
        health = '{"status": "ok"}'
        metrics = """# HELP llamacpp:requests_processing requests_processing
# TYPE llamacpp:requests_processing gauge
llamacpp:requests_processing{slot="0"} 1
llamacpp:prompt_tokens_total 100
llamacpp:prompt_tokens_cached_total 10
llamacpp:tokens_predicted_total 50
llamacpp:prompt_seconds_total 1.5
llamacpp:tokens_predicted_seconds_total 2.5
llamacpp:prompt_tokens_seconds 0.1
llamacpp:predicted_tokens_seconds 0.2
llamacpp:requests_deferred 0
llamacpp:n_tokens_max 8192
"""

        with mock.patch.dict(os.environ, {"LOCAL_AI_API_KEY": "testkey123"}, clear=True):
            with mock.patch("monitoring.check_llama_metrics.urllib.request.urlopen",
                           side_effect=[FakeResponse(health), FakeResponse(metrics)]) as urlopen:
                result = check_llama_metrics.main(["--timeout", str(self.timeout)])

                self.assertEqual(result, 0)

                calls = urlopen.call_args_list
                self.assertEqual(len(calls), 2)
                self.assertEqual(calls[0][1]["timeout"], self.timeout)
                self.assertEqual(calls[1][1]["timeout"], self.timeout)

    def test_missing_key_returns_2(self):
        """Sin fichero ni variable de entorno devuelve 2."""
        with mock.patch.dict(os.environ, {}, clear=True):
            result = check_llama_metrics.main(["--timeout", str(self.timeout)])
            self.assertEqual(result, 2)

    def test_empty_key_file_returns_2(self):
        """Un fichero vacío devuelve 2."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")
            key_file = f.name

        try:
            result = check_llama_metrics.main(["--api-key-file", key_file, "--timeout", str(self.timeout)])
            self.assertEqual(result, 2)
        finally:
            os.unlink(key_file)

    def test_non_positive_timeout_returns_2(self):
        """Timeout cero o negativo devuelve 2."""
        result = check_llama_metrics.main(["--timeout", "0"])
        self.assertEqual(result, 2)

        result = check_llama_metrics.main(["--timeout", "-1"])
        self.assertEqual(result, 2)

    def test_http_failure_returns_3_without_secret(self):
        """Fallo HTTP devuelve 3; la clave de prueba no aparece en stdout ni stderr."""
        health = '{"status": "ok"}'

        stdout_capture = StringIO()
        stderr_capture = StringIO()
        with mock.patch.dict(os.environ, {"LOCAL_AI_API_KEY": "testkey123"}, clear=True), \
             mock.patch("monitoring.check_llama_metrics.urllib.request.urlopen",
                        side_effect=[urllib.error.HTTPError(None, 500, "testkey123", {}, None)]), \
             mock.patch("sys.stdout", stdout_capture), mock.patch("sys.stderr", stderr_capture):
            result = check_llama_metrics.main(["--timeout", str(self.timeout)])
            self.assertEqual(result, 3)
            self.assertNotIn("testkey123", stdout_capture.getvalue())
            self.assertNotIn("testkey123", stderr_capture.getvalue())

    def test_invalid_health_returns_3(self):
        """JSON inválido o status distinto de ok devuelve 3."""
        with mock.patch.dict(os.environ, {"LOCAL_AI_API_KEY": "testkey123"}, clear=True):
            with mock.patch("monitoring.check_llama_metrics.urllib.request.urlopen",
                           side_effect=[FakeResponse("not json")]) as urlopen:
                result = check_llama_metrics.main(["--timeout", str(self.timeout)])
                self.assertEqual(result, 3)

        with mock.patch.dict(os.environ, {"LOCAL_AI_API_KEY": "testkey123"}, clear=True):
            with mock.patch("monitoring.check_llama_metrics.urllib.request.urlopen",
                           side_effect=[FakeResponse('{"status": "error"}')]) as urlopen:
                result = check_llama_metrics.main(["--timeout", str(self.timeout)])
                self.assertEqual(result, 3)

    def test_metrics_network_failure_returns_3(self):
        """Fallo HTTP/red en /metrics devuelve 3."""
        health = '{"status": "ok"}'

        with mock.patch.dict(os.environ, {"LOCAL_AI_API_KEY": "testkey123"}, clear=True):
            with mock.patch("monitoring.check_llama_metrics.urllib.request.urlopen",
                           side_effect=[FakeResponse(health),
                                        urllib.error.HTTPError(None, 503, "Service Unavailable", {}, None)]) as urlopen:
                result = check_llama_metrics.main(["--timeout", str(self.timeout)])
                self.assertEqual(result, 3)

    def test_missing_metric_returns_4(self):
        """Respuesta válida sin requests_deferred devuelve 4."""
        health = '{"status": "ok"}'
        metrics = """# HELP llamacpp:prompt_tokens_total prompt_tokens_total
# TYPE llamacpp:prompt_tokens_total counter
llamacpp:prompt_tokens_total 100
llamacpp:prompt_tokens_cached_total 10
llamacpp:tokens_predicted_total 50
llamacpp:prompt_seconds_total 1.5
llamacpp:tokens_predicted_seconds_total 2.5
llamacpp:prompt_tokens_seconds 0.1
llamacpp:predicted_tokens_seconds 0.2
llamacpp:requests_processing 1
llamacpp:n_tokens_max 8192
"""

        with mock.patch.dict(os.environ, {"LOCAL_AI_API_KEY": "testkey123"}, clear=True):
            with mock.patch("monitoring.check_llama_metrics.urllib.request.urlopen",
                           side_effect=[FakeResponse(health), FakeResponse(metrics)]) as urlopen:
                result = check_llama_metrics.main(["--timeout", str(self.timeout)])
                self.assertEqual(result, 4)

    def test_required_metric_catalog_is_exact(self):
        """El catálogo contiene exactamente las 10 métricas indicadas."""
        self.assertEqual(len(check_llama_metrics.METRICS_CATALOG), 10)
        expected = {
            "llamacpp:prompt_tokens_total",
            "llamacpp:prompt_tokens_cached_total",
            "llamacpp:tokens_predicted_total",
            "llamacpp:prompt_seconds_total",
            "llamacpp:tokens_predicted_seconds_total",
            "llamacpp:prompt_tokens_seconds",
            "llamacpp:predicted_tokens_seconds",
            "llamacpp:requests_processing",
            "llamacpp:requests_deferred",
            "llamacpp:n_tokens_max",
        }
        self.assertEqual(check_llama_metrics.METRICS_CATALOG, expected)

    def test_unexpected_exception_returns_3_without_secret(self):
        """Excepción inesperada devuelve 3 con mensaje fijo; el secreto no aparece."""
        health = '{"status": "ok"}'

        stdout_capture = StringIO()
        stderr_capture = StringIO()
        with mock.patch.dict(os.environ, {"LOCAL_AI_API_KEY": "testkey123"}, clear=True), \
             mock.patch("monitoring.check_llama_metrics.urllib.request.urlopen",
                        side_effect=[FakeResponse(health), RuntimeError("testkey123 leaked")]), \
             mock.patch("sys.stdout", stdout_capture), mock.patch("sys.stderr", stderr_capture):
            result = check_llama_metrics.main(["--timeout", str(self.timeout)])
            self.assertEqual(result, 3)
            self.assertNotIn("testkey123", stdout_capture.getvalue())
            self.assertNotIn("testkey123", stderr_capture.getvalue())


if __name__ == "__main__":
    unittest.main()
