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


def _parse_scalar(value: str) -> Any:
    """Parse a simple scalar from YAML into a Python value.

    This is a minimal helper used only when PyYAML is not available.
    It supports strings, ints, floats, and booleans – enough for
    settings.yaml.
    """
    text = value.strip()
    if not text:
        return ""
    if (text.startswith("\"") and text.endswith("\"")) or (
        text.startswith("'") and text.endswith("'")
    ):
        return text[1:-1]
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        if any(ch in text for ch in [".", "e", "E"]):
            return float(text)
        return int(text)
    except ValueError:
        return text


def _simple_yaml_load(raw: str) -> Dict[str, Any]:
    """Very small YAML loader for settings.yaml when PyYAML is missing.

    Supports only the subset we use: nested dictionaries, lists introduced
    by "- " lines, and basic scalar types. It is **not** a general YAML
    parser but is sufficient to keep JARVIS configurable without
    requiring an external dependency.
    """
    root: Dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    list_keys = {"allowlist_apps", "kill_switch_commands"}

    for raw_line in raw.splitlines():
        # Strip comments and whitespace-only lines
        line = raw_line.split("#", 1)[0].rstrip("\n\r")
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        line = line.lstrip(" ")

        # Adjust stack based on indentation
        while stack and indent <= stack[-1][0] and len(stack) > 1:
            stack.pop()
        current = stack[-1][1]

        if line.startswith("- "):
            # List item
            value = _parse_scalar(line[2:])
            if isinstance(current, list):
                current.append(value)
            else:
                # If current isn't a list, skip gracefully
                continue
            continue

        if ":" in line:
            key, rest = line.split(":", 1)
            key = key.strip()
            rest = rest.strip()

            if rest == "":
                # Nested structure
                if key in list_keys:
                    child: Any = []
                else:
                    child = {}
                if isinstance(current, dict):
                    current[key] = child
                    stack.append((indent, child))
                continue

            # Simple key: value
            if isinstance(current, dict):
                current[key] = _parse_scalar(rest)

    return root


def load_settings(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8")
    # Prefer PyYAML when available
    if yaml is not None:
        try:
            return yaml.safe_load(raw) or {}
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[JARVIS] Failed to parse settings.yaml with PyYAML: {exc}. Falling back to built-in parser.", flush=True)

    # Built-in minimal YAML parser fallback
    try:
        return _simple_yaml_load(raw)
    except Exception as exc:
        print(f"[JARVIS] Could not parse settings.yaml: {exc}. Using empty settings.", flush=True)
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
