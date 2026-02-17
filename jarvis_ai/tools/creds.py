from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from cryptography.fernet import Fernet  # type: ignore

from jarvis_ai.tools.safety import require_confirmation


class CredentialError(RuntimeError):
    pass


@dataclass
class CredentialStore:
    path: Path = Path.home() / ".jarvis_creds.enc"
    key_env: str = "JARVIS_CRED_KEY"
    _cache: Dict[str, str] = field(default_factory=dict, init=False)
    _loaded: bool = field(default=False, init=False)

    def _get_key(self) -> bytes:
        key = os.environ.get(self.key_env)
        if not key:
            raise CredentialError(
                f"Missing encryption key. Set env {self.key_env} to a 32-byte urlsafe base64 key (e.g., Fernet key)."
            )
        return key.encode()

    def _ensure_crypto(self):
        try:
            from cryptography.fernet import Fernet  # type: ignore
        except Exception as exc:
            raise CredentialError("cryptography is not installed. Install with: pip install cryptography") from exc
        return Fernet

    def load(self) -> None:
        if self._loaded:
            return
        if not self.path.exists():
            self._cache = {}
            self._loaded = True
            return
        Fernet = self._ensure_crypto()
        key = self._get_key()
        f = Fernet(key)
        data = self.path.read_bytes()
        decrypted = f.decrypt(data)
        self._cache = json.loads(decrypted.decode("utf-8"))
        self._loaded = True

    def save(self) -> None:
        Fernet = self._ensure_crypto()
        key = self._get_key()
        f = Fernet(key)
        payload = json.dumps(self._cache).encode("utf-8")
        encrypted = f.encrypt(payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(encrypted)

    def set(self, name: str, value: str) -> None:
        self.load()
        self._cache[name] = value
        self.save()

    def get(self, name: str) -> Optional[str]:
        self.load()
        return self._cache.get(name)

    def delete(self, name: str) -> None:
        self.load()
        if name in self._cache:
            if require_confirmation(f"Delete stored credential '{name}'?"):
                self._cache.pop(name, None)
                self.save()
