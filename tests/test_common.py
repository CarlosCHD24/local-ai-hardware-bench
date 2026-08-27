from __future__ import annotations

import stat
import tempfile
import unittest
from pathlib import Path

from local_ai_bench.system.common import executable_version


class CommonSystemTests(unittest.TestCase):
    def test_executable_version_redacts_absolute_binary_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "llama-bench"
            binary.write_text(
                "#!/bin/sh\nprintf 'usage: %s [options]\\n' \"$0\" >&2\n",
                encoding="utf-8",
            )
            binary.chmod(binary.stat().st_mode | stat.S_IXUSR)

            version = executable_version(binary)

            self.assertEqual(version, "usage: llama-bench [options]")
            self.assertNotIn(temp_dir, version or "")


if __name__ == "__main__":
    unittest.main()
