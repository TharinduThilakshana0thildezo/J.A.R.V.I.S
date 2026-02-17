from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from selenium import webdriver  # type: ignore
    from selenium.webdriver.chrome.options import Options  # type: ignore
    from selenium.webdriver.chrome.service import Service  # type: ignore


class BrowserError(RuntimeError):
    pass


@dataclass
class BrowserConfig:
    headless: bool = True
    driver_path: Optional[Path] = None
    default_timeout: float = 15.0


class BrowserSession:
    """Lightweight Selenium wrapper for navigation and form interaction."""

    def __init__(self, config: BrowserConfig) -> None:
        try:
            from selenium import webdriver  # type: ignore
            from selenium.webdriver.chrome.options import Options  # type: ignore
            from selenium.webdriver.chrome.service import Service  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency
            raise BrowserError(
                "selenium is not installed. Install with: pip install selenium"
            ) from exc

        options = Options()
        if config.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        service = None
        if config.driver_path:
            service = Service(executable_path=str(config.driver_path))
        else:
            # Allow override via env if user provides chromedriver location
            driver_env = os.environ.get("CHROMEDRIVER")
            if driver_env:
                service = Service(executable_path=driver_env)

        try:
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as exc:  # pragma: no cover - environment
            raise BrowserError(
                "Failed to start Chrome WebDriver. Ensure Chrome is installed and chromedriver is on PATH or set CHROMEDRIVER env."
            ) from exc

        self.timeout = float(config.default_timeout)

    def close(self) -> None:
        try:
            self.driver.quit()
        except Exception:
            pass

    # Internal helper
    def _wait_for(self, selector: str, timeout: Optional[float] = None):
        try:
            from selenium.webdriver.common.by import By  # type: ignore
            from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
            from selenium.webdriver.support import expected_conditions as EC  # type: ignore
        except Exception as exc:
            raise BrowserError("Selenium support modules missing") from exc

        wait_time = timeout or self.timeout
        return WebDriverWait(self.driver, wait_time).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

    def open(self, url: str) -> None:
        self.driver.get(url)

    def click(self, selector: str, timeout: Optional[float] = None) -> None:
        el = self._wait_for(selector, timeout)
        el.click()

    def fill(self, selector: str, text: str, timeout: Optional[float] = None) -> None:
        el = self._wait_for(selector, timeout)
        el.clear()
        el.send_keys(text)

    def submit(self, selector: str, timeout: Optional[float] = None) -> None:
        el = self._wait_for(selector, timeout)
        try:
            el.submit()
        except Exception:
            el.click()

    def wait_for(self, selector: str, timeout: Optional[float] = None) -> None:
        _ = self._wait_for(selector, timeout)

    def text(self, selector: str, timeout: Optional[float] = None, max_len: int = 4000) -> str:
        el = self._wait_for(selector, timeout)
        val = el.text or el.get_attribute("value") or ""
        if len(val) > max_len:
            val = val[:max_len] + "..."
        return val

    def screenshot(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.driver.save_screenshot(str(path))
        return path
