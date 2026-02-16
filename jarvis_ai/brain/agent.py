from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, Optional

from jarvis_ai.brain.llm import LLMClient
from jarvis_ai.brain.planner import PlanStep, Planner
from jarvis_ai.brain.prompts import DECISION_PROMPT, SYSTEM_PROMPT
from jarvis_ai.brain.reflection import reflect
from jarvis_ai.memory.logs import Logger
from jarvis_ai.memory.long_term import LongTermMemory
from jarvis_ai.memory.short_term import ShortTermMemory
from jarvis_ai.memory.skills import SkillLesson, SkillMemory
from jarvis_ai.tools.apps import open_app
from jarvis_ai.tools.files import read_text, write_text
from jarvis_ai.tools.input import click_mouse, hotkey, move_mouse, send_keys
from jarvis_ai.tools.safety import require_confirmation
from jarvis_ai.tools.system import kill_process, list_processes, system_stats
from jarvis_ai.voice.stt import transcribe
from jarvis_ai.voice.tts import speak
from jarvis_ai.vision.screen import ScreenRegion, ocr_screen
from jarvis_ai.integrations.moltbook import create_post as moltbook_create_post, MoltbookError


@dataclass
class Decision:
    intent: str
    action: str
    action_input: Any
    needs_confirmation: bool


class KillSwitch(Exception):
    pass


@dataclass
class JarvisAgent:
    settings: Dict[str, Any]
    voice_enabled: bool = False
    tts_voice_id: Optional[str] = None
    vision_enabled: bool = False
    ocr_lang: str = "eng"

    def run(self) -> None:
        base_dir = Path(__file__).resolve().parents[1]
        llm_settings = self.settings.get("llm", {})
        memory_settings = self.settings.get("memory", {})
        safety_settings = self.settings.get("safety", {})

        client = LLMClient(
            base_url=llm_settings.get("base_url", "http://localhost:11434"),
            model=llm_settings.get("model", "mistral"),
        )
        planner = Planner()
        short_term = ShortTermMemory()
        long_term = LongTermMemory(path=base_dir / memory_settings.get("long_term_path", "memory/long_term.json"))
        skills = SkillMemory(path=base_dir / memory_settings.get("skills_path", "memory/skills.json"))
        skills.load()
        logger = Logger(path=base_dir / memory_settings.get("logs_path", "logs/actions.jsonl"))

        kill_switches = {cmd.lower() for cmd in safety_settings.get("kill_switch_commands", [])}
        if not kill_switches:
            kill_switches = {"exit", "quit", "kill", "stop"}
        voice_settings = self.settings.get("voice", {})
        self.voice_enabled = bool(voice_settings.get("enabled", False))
        stt_settings = voice_settings.get("stt", {})
        push_to_talk_key = str(stt_settings.get("push_to_talk_key", "right ctrl"))
        # Model path is relative to project root (one level above jarvis_ai)
        project_root = base_dir.parent
        stt_model_path = project_root / str(
            stt_settings.get("model_path", "jarvis_ai/models/vosk-model-small-en-us-0.15")
        )
        stt_sample_rate = int(stt_settings.get("sample_rate", 16000))
        self.tts_voice_id = voice_settings.get("tts_voice_id") or None

        vision_settings = self.settings.get("vision", {})
        self.vision_enabled = bool(vision_settings.get("enabled", False))
        self.ocr_lang = str(vision_settings.get("ocr_lang", "eng"))

        print("STATUS: Online", flush=True)
        print("JARVIS is online. Type a kill-switch command to stop.", flush=True)
        if self.voice_enabled:
            print(f"Push-to-talk enabled. Hold {push_to_talk_key} to speak.", flush=True)
            print(f"Using STT model at: {stt_model_path}", flush=True)

        try:
            while True:
                if self.voice_enabled:
                    try:
                        user_input = transcribe(
                            model_path=stt_model_path,
                            key=push_to_talk_key,
                            sample_rate=stt_sample_rate,
                        ).strip()
                        if user_input:
                            print(f"You> {user_input}", flush=True)
                    except Exception as exc:
                        print(f"[JARVIS][STT] Error: {exc}. Falling back to text input.", flush=True)
                        user_input = input("You> ").strip()
                else:
                    user_input = input("You> ").strip()
                if not user_input:
                    continue
                if user_input.lower() in kill_switches:
                    raise KillSwitch()

                # Fast path for simple commands like "open chrome" even if LLM is unavailable
                if self._handle_quick_command(user_input, safety_settings, logger):
                    continue

                short_term.add(user_input)
                plan = planner.plan(client, user_input)
                outcome, error = self._execute_plan(
                    client=client,
                    planner=planner,
                    plan=plan,
                    user_input=user_input,
                    skills=skills,
                    long_term=long_term,
                    safety_settings=safety_settings,
                    logger=logger,
                )

                reflection = reflect(
                    client=client,
                    task=user_input,
                    decision="plan_execution",
                    outcome=outcome,
                    error=error,
                )
                short_term.add(reflection.summary)
                long_term.add_entry(user_input, tags=["conversation", "user_input"])
                long_term.add_entry(reflection.summary, tags=["reflection"])
                long_term.add_task(goal=user_input, outcome=outcome)
                long_term.save()

                for lesson in reflection.lessons:
                    if lesson.context and lesson.problem and lesson.lesson:
                        skills.upsert(lesson)
                skills.save()
        except KillSwitch:
            print("JARVIS stopped by user.")

    def _handle_quick_command(self, user_input: str, safety_settings: Dict[str, Any], logger: Logger) -> bool:
        """Handle very simple imperative commands without LLM.

        This keeps basic tasks like "open chrome" working even if the local
        model is unavailable or returns invalid JSON.
        Returns True if the command was handled.
        """
        text = user_input.strip().lower()
        if not text:
            return False

        if text.startswith("open ") or text.startswith("launch "):
            # Heuristic mapping from phrases to allowlisted app names
            quick_map = {
                "chrome": "chrome",
                "google chrome": "chrome",
                "edge": "msedge",
                "microsoft edge": "msedge",
                "vs code": "code",
                "visual studio code": "code",
                "code": "code",
                "notepad": "notepad",
                "explorer": "explorer",
                "file explorer": "explorer",
            }
            chosen_app: Optional[str] = None
            for key, app_name in quick_map.items():
                if key in text:
                    chosen_app = app_name
                    break

            if not chosen_app:
                # Fallback: use the last word as app name
                parts = text.split()
                if len(parts) >= 2:
                    chosen_app = parts[-1]

            if not chosen_app:
                print("JARVIS> I didn't recognize which app to open.", flush=True)
                return True

            allowlist = safety_settings.get("allowlist_apps", [])
            try:
                open_app(app_name=chosen_app, allowlist=allowlist, require_confirm=True, logger=logger)
                print(f"JARVIS> Attempting to open {chosen_app} (with your confirmation)", flush=True)
            except Exception as exc:
                print(f"JARVIS> Failed to open {chosen_app}: {exc}", flush=True)
            return True

        return False

    def _decide(
        self,
        client: LLMClient,
        user_input: str,
        plan: list[PlanStep],
        current_step: PlanStep,
        lessons: list[SkillLesson],
        long_term_hits: list[Dict[str, Any]],
    ) -> Decision:
        lessons_text = "\n".join(
            f"- context: {lesson.context}; problem: {lesson.problem}; lesson: {lesson.lesson}; confidence: {lesson.confidence}"
            for lesson in lessons
        )
        prompt = DECISION_PROMPT.format(
            user_input=user_input,
            current_step=current_step.description,
            plan="\n".join(step.description for step in plan),
            lessons=lessons_text or "(none)",
            long_term=self._format_long_term(long_term_hits),
        )

        try:
            response = client.generate(prompt=prompt, system=SYSTEM_PROMPT)
            payload = json.loads(response.text)
        except Exception:
            payload = {
                "intent": "unknown",
                "action": "respond",
                "action_input": "I need more details or the local model is unavailable. Please clarify or check Ollama.",
                "needs_confirmation": False,
            }

        return Decision(
            intent=str(payload.get("intent", "unknown")),
            action=str(payload.get("action", "respond")),
            action_input=payload.get("action_input", ""),
            needs_confirmation=bool(payload.get("needs_confirmation", False)),
        )

    def _execute_plan(
        self,
        client: LLMClient,
        planner: Planner,
        plan: list[PlanStep],
        user_input: str,
        skills: SkillMemory,
        long_term: LongTermMemory,
        safety_settings: Dict[str, Any],
        logger: Logger,
    ) -> tuple[str, Optional[str]]:
        pending_steps = {step.step_id: step for step in plan}
        last_error: Optional[str] = None

        while True:
            ready = planner.ready_steps(list(pending_steps.values()))
            if not ready:
                if pending_steps:
                    print("STATUS: Planning failed", flush=True)
                    return "failed", "No ready steps. Dependency issue or cyclic plan."
                break

            for step in ready:
                print(f"STATUS: Step {step.step_id} - {step.description}", flush=True)
                relevant = skills.relevant(step.description)
                long_term_hits = long_term.search(step.description, top_k=3)
                decision = self._decide(client, user_input, plan, step, relevant, long_term_hits)
                outcome, error = self._act(decision, safety_settings, logger)
                logger.log(
                    task=f"step:{step.step_id}:{step.description}",
                    decision=f"{decision.action}({self._format_action_input(decision.action_input)})",
                    outcome=outcome,
                    error=error,
                )

                if outcome == "success":
                    step.status = "done"
                    print(f"STATUS: Step {step.step_id} done", flush=True)
                else:
                    if relevant:
                        retry_decision = self._decide(
                            client,
                            f"{user_input} (retry using lessons)",
                            plan,
                            step,
                            relevant,
                            long_term_hits,
                        )
                        retry_outcome, retry_error = self._act(retry_decision, safety_settings, logger)
                        logger.log(
                            task=f"step:{step.step_id}:retry",
                            decision=f"{retry_decision.action}({self._format_action_input(retry_decision.action_input)})",
                            outcome=retry_outcome,
                            error=retry_error,
                        )
                        if retry_outcome == "success":
                            step.status = "done"
                            print(f"STATUS: Step {step.step_id} done", flush=True)
                            pending_steps.pop(step.step_id, None)
                            continue
                        last_error = retry_error or error or "step failed"
                    step.status = "failed"
                    last_error = error or "step failed"
                    print(f"STATUS: Step {step.step_id} failed", flush=True)
                    return "failed", last_error

                pending_steps.pop(step.step_id, None)

        print("STATUS: Plan complete", flush=True)
        return "success", last_error

    def _act(self, decision: Decision, safety_settings: Dict[str, Any], logger: Logger) -> tuple[str, Optional[str]]:
        if decision.needs_confirmation and safety_settings.get("require_confirmations", True):
            if not require_confirmation(f"{decision.action} {self._format_action_input(decision.action_input)}"):
                print("Action cancelled by user.")
                return "cancelled", None

        if decision.action == "respond":
            print(f"JARVIS> {decision.action_input}", flush=True)
            if self.voice_enabled:
                speak(str(decision.action_input), voice_id=self.tts_voice_id)
            return "success", None
        if decision.action == "ask_clarification":
            print(f"JARVIS> {decision.action_input}", flush=True)
            if self.voice_enabled:
                speak(str(decision.action_input), voice_id=self.tts_voice_id)
            return "needs_input", None

        if decision.action == "open_app":
            app_name = self._get_field(decision.action_input, "app")
            if not app_name:
                return "failed", "Missing app name"
            allowlist = safety_settings.get("allowlist_apps", [])
            open_app(app_name=app_name, allowlist=allowlist, require_confirm=True, logger=logger)
            return "success", None

        if decision.action == "send_keys":
            text = self._get_field(decision.action_input, "text")
            if not text:
                return "failed", "Missing text"
            send_keys(text=text, require_confirm=True, logger=logger)
            return "success", None

        if decision.action == "hotkey":
            keys = self._get_list(decision.action_input, "keys")
            if not keys:
                return "failed", "Missing hotkey keys"
            hotkey(*keys, require_confirm=True, logger=logger)
            return "success", None

        if decision.action == "move_mouse":
            x = self._get_int(decision.action_input, "x")
            y = self._get_int(decision.action_input, "y")
            duration = float(self._get_field(decision.action_input, "duration") or 0.2)
            if x is None or y is None:
                return "failed", "Missing mouse coordinates"
            move_mouse(x=x, y=y, duration=duration, require_confirm=True, logger=logger)
            return "success", None

        if decision.action == "click_mouse":
            button = self._get_field(decision.action_input, "button") or "left"
            click_mouse(button=button, require_confirm=True, logger=logger)
            return "success", None

        if decision.action == "system_stats":
            stats = system_stats()
            print(f"JARVIS> {stats}", flush=True)
            return "success", None

        if decision.action == "list_processes":
            limit = self._get_int(decision.action_input, "limit") or 10
            processes = list_processes(limit=limit)
            print(f"JARVIS> {processes}", flush=True)
            return "success", None

        if decision.action == "kill_process":
            pid = self._get_int(decision.action_input, "pid")
            if pid is None:
                return "failed", "Missing pid"
            kill_process(pid=pid, require_confirm=True, logger=logger)
            return "success", None

        if decision.action == "read_screen":
            if not self.vision_enabled:
                return "failed", "Vision is disabled"
            region = self._get_region(decision.action_input)
            text = ocr_screen(region=region, lang=self.ocr_lang)
            print(f"JARVIS> {text}", flush=True)
            if self.voice_enabled and text:
                speak(text, voice_id=self.tts_voice_id)
            return "success", None

        if decision.action == "moltbook_post":
            title = self._get_field(decision.action_input, "title")
            content = self._get_field(decision.action_input, "content")
            submolt = self._get_field(decision.action_input, "submolt") or "general"
            if not title or not content:
                return "failed", "Missing title or content for Moltbook post"
            try:
                resp = moltbook_create_post(title=title, content=content, submolt=submolt)
                print(
                    f"JARVIS> Posted to Moltbook m/{submolt}: {title}",
                    flush=True,
                )
                return "success", None
            except MoltbookError as exc:
                print(f"JARVIS> Moltbook error: {exc}", flush=True)
                return "failed", str(exc)
            except Exception as exc:  # pragma: no cover - network
                print(f"JARVIS> Failed to post to Moltbook: {exc}", flush=True)
                return "failed", str(exc)

        if decision.action == "read_file":
            path_str = self._get_field(decision.action_input, "path")
            if not path_str:
                return "failed", "Missing file path"
            root = Path(safety_settings.get("file_root", Path(__file__).resolve().parents[2]))
            path = Path(path_str)
            if not path.is_absolute():
                path = root / path
            try:
                content = read_text(path=path, root=root, require_confirm=True, logger=logger)
            except Exception as exc:
                return "failed", str(exc)
            print(f"JARVIS> [file:{path}]\n{content}", flush=True)
            return "success", None

        if decision.action == "write_file":
            path_str = self._get_field(decision.action_input, "path")
            text = self._get_field(decision.action_input, "text")
            if not path_str or text is None:
                return "failed", "Missing file path or text"
            root = Path(safety_settings.get("file_root", Path(__file__).resolve().parents[2]))
            path = Path(path_str)
            if not path.is_absolute():
                path = root / path
            try:
                write_text(path=path, text=text, root=root, require_confirm=True, logger=logger)
            except Exception as exc:
                return "failed", str(exc)
            print(f"JARVIS> File updated: {path}", flush=True)
            return "success", None

        return "failed", f"Unknown action: {decision.action}"

    def _format_long_term(self, hits: list[Dict[str, Any]]) -> str:
        if not hits:
            return "(none)"
        lines = []
        for item in hits:
            entry = item.get("entry", {})
            text = entry.get("text", "")
            tags = ", ".join(entry.get("tags", []))
            score = item.get("score", 0.0)
            lines.append(f"- score: {score:.2f}; tags: {tags}; text: {text}")
        return "\n".join(lines)

    def _get_field(self, payload: Any, key: str) -> Optional[str]:
        if isinstance(payload, dict):
            value = payload.get(key)
            if value is None:
                return None
            return str(value)
        return None

    def _get_list(self, payload: Any, key: str) -> list[str]:
        if isinstance(payload, dict):
            value = payload.get(key, [])
            if isinstance(value, list):
                return [str(item) for item in value]
        return []

    def _get_int(self, payload: Any, key: str) -> Optional[int]:
        if isinstance(payload, dict) and key in payload:
            try:
                return int(payload[key])
            except Exception:
                return None
        return None

    def _format_action_input(self, payload: Any) -> str:
        if isinstance(payload, dict):
            return json.dumps(payload)
        return str(payload)

    def _get_region(self, payload: Any) -> Optional[ScreenRegion]:
        if not isinstance(payload, dict):
            return None
        region = payload.get("region")
        if not isinstance(region, dict):
            return None
        left = self._get_int(region, "left")
        top = self._get_int(region, "top")
        width = self._get_int(region, "width")
        height = self._get_int(region, "height")
        if left is None or top is None or width is None or height is None:
            return None
        return ScreenRegion(left=left, top=top, width=width, height=height)
