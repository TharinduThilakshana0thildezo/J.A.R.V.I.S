from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    import requests  # type: ignore
except Exception:
    requests = None


@dataclass
class HttpResponse:
    url: str
    status: int
    content: str


class HttpError(RuntimeError):
    pass


def http_get(url: str, timeout: float = 15.0, max_bytes: int = 100_000) -> HttpResponse:
    """Simple HTTP GET for text content.

    - Only allows http/https URLs.
    - Truncates very large responses to max_bytes.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise HttpError(f"Unsupported URL scheme: {parsed.scheme}")

    req = urllib.request.Request(url, headers={"User-Agent": "JarvisLocal/1.0"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            raw = resp.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:  # pragma: no cover - network
        detail = exc.read().decode("utf-8", errors="ignore")
        raise HttpError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover - network
        raise HttpError(f"Connection error: {exc.reason}") from exc

    if len(raw) > max_bytes:
        raw = raw[:max_bytes]

    content = raw.decode("utf-8", errors="replace")
    return HttpResponse(url=url, status=status, content=content)


def http_post_json(url: str, payload: Dict[str, Any], timeout: float = 15.0) -> HttpResponse:
    if requests is None:
        raise HttpError("requests is not installed. Install with: pip install requests")
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except Exception as exc:  # pragma: no cover - network
        raise HttpError(f"Connection error: {exc}") from exc
    text = resp.text or ""
    return HttpResponse(url=resp.url, status=resp.status_code, content=text)


def download_file(url: str, path: Path, timeout: float = 30.0, max_bytes: int = 20_000_000) -> Path:
    if requests is None:
        raise HttpError("requests is not installed. Install with: pip install requests")
    try:
        with requests.get(url, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            path.parent.mkdir(parents=True, exist_ok=True)
            total = 0
            with path.open("wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        raise HttpError("Download exceeds size limit")
                    f.write(chunk)
    except requests.exceptions.RequestException as exc:  # pragma: no cover - network
        raise HttpError(f"Download failed: {exc}") from exc
    return path


def extract_links(html: str, base: Optional[str] = None, limit: int = 50) -> List[str]:
    from html.parser import HTMLParser

    class _LinkParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.links: List[str] = []

        def handle_starttag(self, tag, attrs):
            if tag != "a":
                return
            href = dict(attrs).get("href")
            if not href:
                return
            self.links.append(href)

    parser = _LinkParser()
    parser.feed(html)
    links = parser.links[:limit]
    if base:
        links = [urllib.parse.urljoin(base, l) for l in links]
    return links
