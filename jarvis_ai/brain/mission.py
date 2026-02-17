from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from jarvis_ai.tools.browser import BrowserSession
from jarvis_ai.tools.web import http_get, http_post_json, download_file, extract_links, HttpError
from jarvis_ai.tools.docs import pdf_text, DocError


class MissionError(RuntimeError):
    pass


@dataclass
class MissionResult:
    logs: List[str]

    def as_text(self) -> str:
        return "\n".join(self.logs)


class MissionRunner:
    """Minimal mission runner that sequences browser + HTTP + doc steps."""

    def __init__(self, browser: BrowserSession) -> None:
        self.browser = browser

    def run(self, steps: List[Dict[str, Any]]) -> MissionResult:
        logs: List[str] = []
        total = len(steps)
        for idx, step in enumerate(steps, start=1):
            action = str(step.get("action", "")).lower()
            data = step.get("input", {})
            next_action = steps[idx]["action"] if idx < total and isinstance(steps[idx], dict) else "complete"

            logs.append(self._report(
                status="PLAN",
                current=f"Step {idx}/{total}: {action}",
                result="Planned",
                nxt=f"ACT on {action}",
            ))

            try:
                logs.append(self._report(
                    status="ACT",
                    current=f"Step {idx}/{total}: {action}",
                    result="Executing",
                    nxt="OBSERVE",
                ))
                result_summary = self._execute(action, data)
                logs.append(self._report(
                    status="OBSERVE",
                    current=f"Step {idx}/{total}: {action}",
                    result=result_summary,
                    nxt=f"ADAPT or move to {next_action}",
                ))
            except (HttpError, DocError, MissionError) as exc:
                logs.append(self._report(
                    status="ADAPT",
                    current=f"Step {idx}/{total}: {action}",
                    result=f"Failed: {exc}",
                    nxt="Retry with corrected inputs or credentials",
                ))
                raise MissionError(f"Step {idx} failed ({action}): {exc}") from exc
            except Exception as exc:
                logs.append(self._report(
                    status="ADAPT",
                    current=f"Step {idx}/{total}: {action}",
                    result=f"Unexpected error: {exc}",
                    nxt="Investigate and retry",
                ))
                raise MissionError(f"Step {idx} failed ({action}): {exc}") from exc

            logs.append(self._report(
                status="COMPLETE",
                current=f"Step {idx}/{total}: {action}",
                result="Done",
                nxt="Next step" if idx < total else "Mission complete",
            ))

        return MissionResult(logs=logs)

    def _execute(self, action: str, data: Dict[str, Any]) -> str:
        if action == "browser_open":
            url = self._require(data, "url")
            self.browser.open(url)
            return f"Opened {url}"

        if action == "browser_fill":
            selector = self._require(data, "selector")
            text = str(data.get("text", ""))
            self.browser.fill(selector, text)
            return f"Filled {selector}"

        if action == "browser_click":
            selector = self._require(data, "selector")
            self.browser.click(selector)
            return f"Clicked {selector}"

        if action == "browser_submit":
            selector = self._require(data, "selector")
            self.browser.submit(selector)
            return f"Submitted {selector}"

        if action == "browser_wait":
            selector = self._require(data, "selector")
            self.browser.wait_for(selector)
            return f"Waited for {selector}"

        if action == "browser_text":
            selector = self._require(data, "selector")
            text_val = self.browser.text(selector)
            return f"Text[{selector}]: {text_val[:200]}"

        if action == "browser_screenshot":
            path = Path(str(data.get("path", "./logs/mission.png")))
            out = self.browser.screenshot(path)
            return f"Screenshot {out}"

        if action == "http_get":
            url = self._require(data, "url")
            resp = http_get(url)
            snippet = resp.content[:200]
            return f"http_get {url} status={resp.status} body={snippet}"

        if action == "http_post":
            url = self._require(data, "url")
            payload = data if isinstance(data, dict) else {}
            resp = http_post_json(url, payload=payload)
            snippet = resp.content[:200]
            return f"http_post {url} status={resp.status} body={snippet}"

        if action == "download":
            url = self._require(data, "url")
            path = Path(str(data.get("path", "./downloads/file.bin")))
            out = download_file(url, path)
            return f"Downloaded to {out}"

        if action == "pdf_text":
            path = Path(self._require(data, "path"))
            txt = pdf_text(path)
            return f"pdf_text {path}: {txt[:200]}"

        if action == "extract_links":
            html = str(data.get("html", ""))
            base = data.get("base")
            links = extract_links(html, base=base)
            return "links: " + ", ".join(links)

        raise MissionError(f"Unknown action: {action}")

    def _require(self, payload: Dict[str, Any], key: str) -> str:
        if not isinstance(payload, dict):
            raise MissionError("Invalid payload; expected object")
        val = payload.get(key)
        if val is None or val == "":
            raise MissionError(f"Missing required field: {key}")
        return str(val)

    def _report(self, status: str, current: str, result: str, nxt: str) -> str:
        return (
            f"STATUS: {status}\n"
            f"CURRENT ACTION: {current}\n"
            f"RESULT: {result}\n"
            f"NEXT STEP: {nxt}\n"
        )
