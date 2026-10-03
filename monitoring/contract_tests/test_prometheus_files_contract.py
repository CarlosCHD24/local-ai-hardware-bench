import unittest
from pathlib import Path

from monitoring import validate_prometheus


ROOT = Path(__file__).resolve().parents[2]


class PrometheusFilesContract(unittest.TestCase):
    def test_config_is_local_and_valid(self):
        config = ROOT / "monitoring/prometheus/prometheus.yml"
        self.assertEqual(validate_prometheus.main(["--config", str(config)]), 0)
        text = config.read_text()
        self.assertIn("192.168.3.42:8080", text)
        self.assertNotIn("Bearer ", text)

    def test_node_exporter_is_loopback_with_textfile_collector(self):
        text = (ROOT / "monitoring/systemd/node-exporter.service").read_text()
        self.assertIn("--web.listen-address=127.0.0.1:9100", text)
        self.assertIn("--collector.textfile.directory=/var/lib/node_exporter/textfile_collector", text)
