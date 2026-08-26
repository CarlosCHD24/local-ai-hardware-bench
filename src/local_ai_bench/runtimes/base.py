from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class RuntimeAdapter(ABC):
    @abstractmethod
    def prepare(self) -> Path:
        """Prepare the runtime and return its benchmark binary."""

    @abstractmethod
    def command(
        self,
        model_path: Path,
        scenario: dict[str, Any],
        repetitions: int,
        threads: int | None = None,
    ) -> list[str]:
        """Construct a benchmark command."""

    @abstractmethod
    def parse(self, output: str) -> list[dict[str, Any]]:
        """Parse raw output into runtime records."""
