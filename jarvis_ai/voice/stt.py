from __future__ import annotations

import json
import queue
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

try:
    import keyboard  # type: ignore
except Exception:  # pragma: no cover
    keyboard = None

try:
    import sounddevice as sd  # type: ignore
except Exception:  # pragma: no cover
    sd = None

try:
    import vosk  # type: ignore
except Exception:  # pragma: no cover
    vosk = None


@dataclass
class STTConfig:
    model_path: Path
    sample_rate: int = 16000
    block_size: int = 8000


class VoskSTT:
    def __init__(self, config: STTConfig) -> None:
        if vosk is None:
            raise RuntimeError("vosk package is not installed")
        self.config = config
        self._vosk = cast(Any, vosk)
        self.model = self._vosk.Model(str(self.config.model_path))

    def transcribe_push_to_talk(self, key: str) -> str:
        if keyboard is None:
            raise RuntimeError("keyboard package is not installed")
        if sd is None:
            raise RuntimeError("sounddevice package is not installed")
        audio_queue: queue.Queue[bytes] = queue.Queue()

        def callback(indata, frames, time, status) -> None:
            _ = frames, time, status
            audio_queue.put(bytes(indata))

        print(f"Hold {key} to talk...")
        keyboard.wait(key)

        recognizer = self._vosk.KaldiRecognizer(self.model, self.config.sample_rate)
        with sd.RawInputStream(
            samplerate=self.config.sample_rate,
            blocksize=self.config.block_size,
            dtype="int16",
            channels=1,
            callback=callback,
        ):
            while keyboard.is_pressed(key):
                data = audio_queue.get()
                recognizer.AcceptWaveform(data)

        result = json.loads(recognizer.FinalResult()).get("text", "")
        return result.strip()


def transcribe(model_path: Path, key: str, sample_rate: int = 16000) -> str:
    if vosk is None:
        raise RuntimeError("vosk package is not installed")
    if keyboard is None:
        raise RuntimeError("keyboard package is not installed")
    if sd is None:
        raise RuntimeError("sounddevice package is not installed")
    config = STTConfig(model_path=model_path, sample_rate=sample_rate)
    stt = VoskSTT(config)
    return stt.transcribe_push_to_talk(key)
