from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SETTINGS_PATH = REPO_ROOT / "config" / "settings.yaml"


def load_settings(path: Path | None = None) -> dict:
    settings_path = path or DEFAULT_SETTINGS_PATH
    with settings_path.open() as f:
        return yaml.safe_load(f)
