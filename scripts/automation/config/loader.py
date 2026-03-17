"""설정 파일 로더"""

import yaml
from pathlib import Path

_CONFIG = None


def load_config() -> dict:
    global _CONFIG
    if _CONFIG is None:
        config_path = Path(__file__).parent / "settings.yaml"
        with open(config_path, encoding="utf-8") as f:
            _CONFIG = yaml.safe_load(f)
    return _CONFIG
