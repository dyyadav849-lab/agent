from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def is_local_file(path: str) -> bool:
    """Check if the input path is a local file path"""
    return Path(path).exists()


def load_yaml_file(yaml_path: str) -> dict[str, Any]:
    """Load input YAML file"""
    with Path.open(yaml_path) as stream:
        return yaml.safe_load(stream)


def load_json_file(json_path: str) -> dict[str, Any]:
    """Load input JSON file"""
    with Path.open(json_path, "r", encoding="utf-8") as stream:
        return json.load(stream)
