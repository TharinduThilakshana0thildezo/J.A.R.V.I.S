from pathlib import Path

from jarvis_ai.tools.safety import is_allowed_app, is_path_allowed


def test_is_allowed_app() -> None:
    assert is_allowed_app("chrome", ["chrome", "notepad"])
    assert not is_allowed_app("calc", ["chrome", "notepad"])
    assert not is_allowed_app("chrome", [])


def test_is_path_allowed() -> None:
    root = Path("C:/Users")
    allowed = Path("C:/Users/Test/file.txt")
    blocked = Path("C:/Windows/System32")
    assert is_path_allowed(allowed, root)
    assert not is_path_allowed(blocked, root)
