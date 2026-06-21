import yaml
from pathlib import Path


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))
