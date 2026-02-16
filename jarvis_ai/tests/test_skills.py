from pathlib import Path
import tempfile

from jarvis_ai.memory.skills import SkillLesson, SkillMemory


def test_skills_upsert_and_relevant() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "skills.json"
        memory = SkillMemory(path)
        memory.load()

        lesson = SkillLesson(
            context="open_app",
            problem="app name mismatch",
            lesson="Try alternative app names",
            confidence=0.8,
        )
        memory.upsert(lesson)
        memory.save()

        memory.load()
        hits = memory.relevant("Please open_app chrome")
        assert hits
        assert hits[0].context == "open_app"
