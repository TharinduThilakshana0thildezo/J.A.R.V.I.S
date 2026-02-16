from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

API_BASE = "https://www.moltbook.com/api/v1"
DEFAULT_CREDENTIALS_PATH = Path.home() / ".config" / "moltbook" / "credentials.json"


@dataclass
class MoltbookResponse:
    success: bool
    data: Dict[str, Any]
    raw: Dict[str, Any]


class MoltbookError(RuntimeError):
    pass


def load_api_key(env_var: str = "MOLTBOOK_API_KEY", credentials_path: Optional[Path] = None) -> str:
    """Load Moltbook API key from env or credentials file.

    Follows the SKILL.md recommendation: prefer env var, then
    ~/.config/moltbook/credentials.json with {"api_key": "..."}.
    """
    key = os.getenv(env_var)
    if key:
        return key

    path = credentials_path or DEFAULT_CREDENTIALS_PATH
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            key = data.get("api_key")
            if key:
                return str(key)
    except Exception:
        # Fall through to error below
        pass

    raise MoltbookError(
        "Moltbook API key not found. Set MOLTBOOK_API_KEY or create "
        "~/.config/moltbook/credentials.json with {\"api_key\": \"...\"}."
    )


def _request(method: str, path: str, api_key: str, body: Optional[Dict[str, Any]] = None) -> MoltbookResponse:
    if not path.startswith("/"):
        path = "/" + path
    url = API_BASE + path

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    data_bytes: Optional[bytes] = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data_bytes = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method.upper())

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw_text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:  # pragma: no cover - network
        detail = exc.read().decode("utf-8", errors="ignore")
        raise MoltbookError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover - network
        raise MoltbookError(f"Connection error: {exc.reason}") from exc

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise MoltbookError("Invalid JSON response from Moltbook") from exc

    success = bool(parsed.get("success", True))
    data = parsed.get("data") or parsed
    if not success:
        error_msg = parsed.get("error") or "Unknown Moltbook error"
        hint = parsed.get("hint")
        if hint:
            error_msg = f"{error_msg} (hint: {hint})"
        raise MoltbookError(error_msg)

    return MoltbookResponse(success=True, data=data, raw=parsed)


def create_post(title: str, content: str, submolt: str = "general", api_key: Optional[str] = None) -> MoltbookResponse:
    """Create a text post on Moltbook.

    Mirrors SKILL.md example:
    curl -X POST https://www.moltbook.com/api/v1/posts ...
    """
    key = api_key or load_api_key()
    body = {
        "submolt": submolt,
        "title": title,
        "content": content,
    }
    return _request("POST", "/posts", api_key=key, body=body)


def get_feed(sort: str = "hot", limit: int = 10, api_key: Optional[str] = None) -> MoltbookResponse:
    key = api_key or load_api_key()
    params = urllib.parse.urlencode({"sort": sort, "limit": int(limit)})
    return _request("GET", f"/feed?{params}", api_key=key)
