import tempfile
import unittest
from pathlib import Path
from unittest import mock

from monitoring import nvidia_textfile


class NvidiaTextfileContract(unittest.TestCase):
    def test_success_replaces_complete_metric_file(self):
        def successful_collection(argv):
            print("local_ai_gpu_scrape_success 1")
            return 0

        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "monitoring.nvidia_textfile.nvidia_metrics.main", side_effect=successful_collection
        ):
            self.assertEqual(nvidia_textfile.main(["--directory", tmp]), 0)
            self.assertEqual(
                (Path(tmp) / nvidia_textfile.NAME).read_text(),
                "local_ai_gpu_scrape_success 1\n",
            )

    def test_failure_writes_only_failure_metric(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "monitoring.nvidia_textfile.nvidia_metrics.main", return_value=3
        ):
            self.assertEqual(nvidia_textfile.main(["--directory", tmp]), 3)
            self.assertEqual(
                (Path(tmp) / nvidia_textfile.NAME).read_text(),
                "local_ai_gpu_scrape_success 0\n",
            )

    def test_invalid_arguments_do_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(nvidia_textfile.main(["--directory", tmp, "--timeout", "0"]), 2)
            self.assertFalse((Path(tmp) / nvidia_textfile.NAME).exists())
