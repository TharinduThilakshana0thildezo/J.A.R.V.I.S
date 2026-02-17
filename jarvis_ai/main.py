from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

# Ensure project root (containing the jarvis_ai package) is on sys.path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency for now
    yaml = None

from jarvis_ai.brain.agent import JarvisAgent


def load_settings(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8")
    if yaml:
        return yaml.safe_load(raw) or {}
    # Fallback: tolerate YAML-style files even without PyYAML
    try:
        return json.loads(raw)
    except Exception:
        print("[JARVIS] settings.yaml is YAML; install pyyaml or convert to JSON. Falling back to empty settings.", flush=True)
        return {}


def main() -> None:
    settings_path = Path(__file__).parent / "config" / "settings.yaml"
    settings = load_settings(settings_path)
    # If launched in text-panel mode, force voice off so user can type commands
    if os.environ.get("JARVIS_TEXT_ONLY") == "1":
        voice_cfg = settings.get("voice") or {}
        voice_cfg["enabled"] = False
        settings["voice"] = voice_cfg
    agent = JarvisAgent(settings=settings)
    agent.run()


if __name__ == "__main__":
    main()
