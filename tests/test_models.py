from __future__ import annotations

import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from local_ai_bench.models import artifact_verified, update_verify_cache, verify_artifact


class ModelTests(unittest.TestCase):
    def test_verify_and_cache_small_artifact(self) -> None:
        content = b"reproducible model fixture"
        artifact = {
            "filename": "model.gguf",
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        with TemporaryDirectory() as directory_text:
            directory = Path(directory_text)
            path = directory / artifact["filename"]
            path.write_bytes(content)
            verify_artifact(path, artifact)
            update_verify_cache(directory, artifact)
            self.assertTrue(artifact_verified(path, artifact, directory / ".verified.json"))


if __name__ == "__main__":
    unittest.main()
