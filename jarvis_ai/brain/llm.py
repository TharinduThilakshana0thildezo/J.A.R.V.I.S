from __future__ import annotations

from dataclasses import dataclass
import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


@dataclass
class LLMResponse:
    text: str
    raw: Dict[str, Any]


class LLMClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float = 60.0,
        provider: str = "ollama",
        api_key: Optional[str] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.provider = provider.lower()
        self.api_key = api_key
        verbose_flag = os.getenv("JARVIS_LLM_VERBOSE", "").lower()
        self.verbose = verbose_flag in {"1", "true", "yes", "on"}

    def generate(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        if self.provider == "openai":
            return self._generate_openai(prompt, system)
        elif self.provider == "groq":
            return self._generate_groq(prompt, system)
        return self._generate_ollama(prompt, system)

    def _generate_ollama(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        url = f"{self.base_url}/api/generate"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                parsed = json.loads(raw)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Ollama HTTP error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama connection error: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Invalid JSON response from Ollama") from exc

        text = parsed.get("response", "")
        if not str(text).strip():
            raise RuntimeError("Ollama returned an empty response")
        return LLMResponse(text=text, raw=parsed)

    def _generate_openai(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
        }

        url = "https://api.openai.com/v1/chat/completions"
        data = json.dumps(payload).encode("utf-8")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                parsed = json.loads(raw)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"OpenAI HTTP error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI connection error: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Invalid JSON response from OpenAI") from exc

        try:
            text = parsed["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            text = ""
            
        return LLMResponse(text=text, raw=parsed)

    def _generate_groq(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        """Generate using Groq's free API (compatible with OpenAI format)."""
        try:
            import requests
        except ImportError:
            raise RuntimeError("requests library required for Groq. Install with: pip install requests")
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
        }

        url = "https://api.groq.com/openai/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "JARVIS/1.0",
        }
        
        try:
            if self.verbose:
                print(f"[JARVIS][LLM] Sending request to {url}", flush=True)
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            if self.verbose:
                print(f"[JARVIS][LLM] Response status: {response.status_code}", flush=True)
            response.raise_for_status()
            parsed = response.json()
        except requests.exceptions.HTTPError as exc:
            msg = f"Groq HTTP error {exc.response.status_code}: {exc.response.text}"
            if exc.response.status_code == 429:
                msg = f"Rate limit reached (429): {exc.response.text}"
            raise RuntimeError(msg) from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Groq connection error: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError("Invalid JSON response from Groq") from exc

        try:
            text = parsed["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            text = ""
            
        return LLMResponse(text=text, raw=parsed)


