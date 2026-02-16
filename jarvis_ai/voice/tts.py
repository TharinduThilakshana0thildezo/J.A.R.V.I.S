from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:
    import pyttsx3  # type: ignore
except Exception:  # pragma: no cover
    pyttsx3 = None


@dataclass
class TTSConfig:
    voice_id: Optional[str] = None
    rate: int = 180
    volume: float = 1.0


class Pyttsx3TTS:
    def __init__(self, config: TTSConfig) -> None:
        if pyttsx3 is None:
            raise RuntimeError("pyttsx3 package is not installed")
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", config.rate)
        self.engine.setProperty("volume", config.volume)
        if config.voice_id:
            self.engine.setProperty("voice", config.voice_id)

    def speak(self, text: str) -> None:
        self.engine.say(text)
        self.engine.runAndWait()


def speak(text: str, voice_id: Optional[str] = None) -> None:
    if pyttsx3 is None:
        raise RuntimeError("pyttsx3 package is not installed")
    tts = Pyttsx3TTS(TTSConfig(voice_id=voice_id))
    tts.speak(text)
