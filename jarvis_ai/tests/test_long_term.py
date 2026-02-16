from pathlib import Path
import tempfile

from jarvis_ai.memory.long_term import LongTermMemory


def test_long_term_add_and_search() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "long_term.json"
        memory = LongTermMemory(path)
        memory.add_entry("Remember the launch code is 1234", tags=["note"])
        memory.add_entry("Meeting at 3pm", tags=["calendar"])
        memory.save()

        hits = memory.search("launch code", top_k=1)
        assert hits
        assert "launch code" in hits[0]["entry"]["text"].lower()
