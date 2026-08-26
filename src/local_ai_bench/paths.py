from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    override = os.environ.get("LOCAL_AI_BENCH_PROJECT")
    if override:
        return Path(override).expanduser().resolve()

    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "suites").is_dir() and (candidate / "models").is_dir():
        return candidate
    return Path.cwd().resolve()


def data_home(root: Path | None = None) -> Path:
    override = os.environ.get("LOCAL_AI_BENCH_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return (root or project_root()) / ".local-ai-bench"


def suite_path(suite: str, root: Path | None = None) -> Path:
    requested = Path(suite)
    if requested.is_file():
        return requested.resolve()
    name = suite if suite.endswith(".json") else f"{suite}.json"
    return (root or project_root()) / "suites" / name
