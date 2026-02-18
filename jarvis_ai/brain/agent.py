from __future__ import annotations

from dataclasses import dataclass
import ast
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from jarvis_ai.brain.llm import LLMClient, LLMResponse
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
from jarvis_ai.tools.browser import BrowserSession, BrowserConfig, BrowserError
from jarvis_ai.tools.creds import CredentialStore, CredentialError
from jarvis_ai.tools.safety import require_confirmation
from jarvis_ai.tools.system import kill_process, list_processes, system_stats
from jarvis_ai.tools.web import http_get, http_post_json, download_file, extract_links, HttpError, HttpResponse
from jarvis_ai.tools.docs import pdf_text, DocError, sniff_verification_tokens
from jarvis_ai.brain.mission import MissionRunner, MissionError
from jarvis_ai.voice.stt import transcribe, is_stt_available
from jarvis_ai.voice.tts import speak
from jarvis_ai.vision.screen import ScreenRegion, ocr_screen
from jarvis_ai.integrations.moltbook import create_post as moltbook_create_post, MoltbookError
import webbrowser


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
    groq_cooldown_until: float = 0.0
    openai_cooldown_until: float = 0.0
    local_available: bool = False
    browser_session: Optional[BrowserSession] = None

    def _generate_with_fallback(self, prompt: str, system: Optional[str] = None, force_local: bool = False) -> LLMResponse:
        """Generate a response using the 3-tier fallback (Groq -> OpenAI -> Ollama)."""
        llm_settings = self.settings.get("llm", {})
        # Normalize provider and auto-upgrade from pure local to hybrid when a
        # cloud key is configured. This ensures that if you have a Groq/OpenAI
        # key set in settings.yaml, JARVIS will actually use it instead of
        # staying locked to the local backend.
        provider = str(llm_settings.get("provider", "hybrid") or "hybrid").lower()
        groq_key = (llm_settings.get("groq", {}) or {}).get("api_key") or ""
        openai_key = (llm_settings.get("openai", {}) or {}).get("api_key") or ""
        now = time.time()

        # If the config says "ollama" but a cloud key is present, treat this as
        # hybrid so Groq/OpenAI are tried first and local remains a fallback.
        if provider == "ollama" and (groq_key or openai_key):
            provider = "hybrid"

        # If explicitly local or provider is locked to ollama
        if force_local or provider == "ollama":
            print("BRAIN USED: LOCAL", flush=True)
            return self.local_client.generate(prompt, system)

        # Tier 1: Groq (Primary Cloud)
        if provider in ["hybrid", "groq"] and groq_key:
            if now >= self.groq_cooldown_until:
                try:
                    response = self.groq_client.generate(prompt, system)
                    print("BRAIN USED: GROQ", flush=True)
                    return response
                except Exception as e:
                    cooldown = 300.0 if ("429" in str(e) or "rate limit" in str(e).lower()) else 30.0
                    self.groq_cooldown_until = now + cooldown
                    print(f"[JARVIS] Groq failed ({e}). Cooling down for {cooldown}s.", flush=True)
                    if provider != "hybrid": raise e
            else:
                print("BRAIN USED: SKIPPING GROQ (Cooldown active)", flush=True)

        # Tier 2: OpenAI (Secondary Cloud)
        if provider in ["hybrid", "openai"] and openai_key:
            if now >= self.openai_cooldown_until:
                try:
                    response = self.openai_client.generate(prompt, system)
                    print("BRAIN USED: OPENAI", flush=True)
                    return response
                except Exception as e:
                    cooldown = 300.0 if ("429" in str(e) or "rate limit" in str(e).lower()) else 30.0
                    self.openai_cooldown_until = now + cooldown
                    print(f"[JARVIS] OpenAI failed ({e}). Cooling down for {cooldown}s.", flush=True)
                    if provider != "hybrid": raise e
            else:
                print("BRAIN USED: SKIPPING OPENAI (Cooldown active)", flush=True)

        # Tier 3: Ollama (Local Fallback)
        print("BRAIN USED: LOCAL (Tier 3 Fallback)", flush=True)
        try:
            # Re-check availability in case Ollama was started after launch.
            if not self.local_available:
                self.local_available = self._check_local_ollama()
            if not self.local_available:
                raise RuntimeError("Local Ollama not reachable (health check failed)")
            return self.local_client.generate(prompt, system)
        except Exception as e:
            # Never fail silently—surface a user-facing fallback so the agent still answers.
            print(f"[JARVIS] Local fallback failed: {e}", flush=True)
            return LLMResponse(
                text=(
                    "I could not reach any model (Groq, OpenAI, or the local Ollama backend). "
                    "Please check that Ollama is running at http://localhost:11434 or set a working provider. "
                    "You can still ask me to run quick commands like opening apps or searching the web."
                ),
                raw={"error": str(e)},
            )

    def run(self) -> None:
        base_dir = Path(__file__).resolve().parents[1]
        llm_settings = self.settings.get("llm", {})
        memory_settings = self.settings.get("memory", {})
        safety_settings = self.settings.get("safety", {})
        
        provider = llm_settings.get("provider", "hybrid")
        
        # Initialize Clients
        local_timeout = float(
            llm_settings.get("ollama", {}).get("timeout", llm_settings.get("timeout", 60.0))
        )
        # Cap local timeout, but allow enough time for first-load of the model on Ollama.
        local_timeout = min(local_timeout, 120.0)

        self.local_client = LLMClient(
            base_url=llm_settings.get("ollama", {}).get("base_url", "http://localhost:11434"),
            model=llm_settings.get("ollama", {}).get("model", llm_settings.get("model", "mistral")),
            timeout=local_timeout,
            provider="ollama"
        )
        
        self.groq_client = LLMClient(
            base_url="", 
            model=llm_settings.get("groq", {}).get("model", "llama-3.3-70b-versatile"),
            timeout=float(llm_settings.get("timeout", 60.0)),
            provider="groq",
            api_key=llm_settings.get("groq", {}).get("api_key")
        )

        self.openai_client = LLMClient(
            base_url="",
            model=llm_settings.get("openai", {}).get("model", "gpt-4o"),
            timeout=float(llm_settings.get("timeout", 60.0)),
            provider="openai",
            api_key=llm_settings.get("openai", {}).get("api_key")
        )

        self.local_available = self._check_local_ollama()
        if not self.local_available:
            print("[JARVIS] Local Ollama not reachable. Start it with 'ollama serve' and ensure port 11434 is free.", flush=True)

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
        # If STT dependencies (keyboard/sounddevice/vosk) are unavailable,
        # disable voice once up-front to avoid noisy errors on every loop.
        if self.voice_enabled and not is_stt_available():
            print("[JARVIS][STT] Voice input disabled (missing keyboard/sounddevice/vosk). Using text input only.", flush=True)
            self.voice_enabled = False
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

                # Handle explicit memory commands
                if self._handle_remember_command(user_input, long_term, short_term):
                    continue

                # Instant path for greetings/common phrases (0 latency)
                if self._handle_heuristic_response(user_input, long_term, short_term):
                    continue

                # Directly answer identity/name queries without LLM when possible
                if self._handle_identity_query(user_input, long_term, short_term):
                    continue

                short_term.add(user_input)

                # Search memory and format history BEFORE planning
                history_text = "\n".join(short_term.recent(limit=10))
                memory_hits = long_term.search(user_input, top_k=5)
                memory_text = self._format_long_term(memory_hits)

                # Use hybrid generation for planning
                # We wrap the generate method to use failover
                class HybridClient(LLMClient):
                    """Lightweight adapter to reuse the 3-tier fallback with LLMClient typing."""

                    def __init__(self, agent: "JarvisAgent") -> None:
                        super().__init__(base_url="", model="hybrid", provider="ollama")
                        self.agent = agent

                    def generate(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
                        return self.agent._generate_with_fallback(prompt, system)

                hybrid_client = HybridClient(self)
                plan, fast_response = planner.plan(hybrid_client, user_input, history=history_text, memory=memory_text)

                if fast_response:
                    print(f"JARVIS> {fast_response}", flush=True)
                    if self.voice_enabled:
                         speak(fast_response, voice_id=self.tts_voice_id)
                    short_term.add(fast_response)
                    # Save chat to long-term memory as requested
                    long_term.add_entry(f"User: {user_input}\nJARVIS: {fast_response}", tags=["chat", "conversation"])
                    long_term.save()
                    continue

                outcome, error = self._execute_plan(
                    client=hybrid_client,
                    planner=planner,
                    plan=plan,
                    user_input=user_input,
                    skills=skills,
                    long_term=long_term,
                    safety_settings=safety_settings,
                    logger=logger,
                )

                reflection = reflect(
                    client=hybrid_client,
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

        if text.startswith("go to ") or (text.startswith("open ") and ("." in text or "http" in text)):
            target = text.replace("go to ", "").replace("open ", "").strip()
            if not target.startswith("http"):
                target = "https://" + target
            print(f"JARVIS> Opening {target}...", flush=True)
            try:
                webbrowser.open(target)
                if self.voice_enabled:
                     speak(f"Opening {target}", voice_id=self.tts_voice_id)
            except Exception as exc:
                print(f"JARVIS> Failed to open URL: {exc}", flush=True)
            return True

        if text.startswith("play "):
            query = text.replace("play ", "").strip()
            url = f"https://www.youtube.com/results?search_query={query}"
            print(f"JARVIS> Playing {query} on YouTube...", flush=True)
            try:
                webbrowser.open(url)
                if self.voice_enabled:
                     speak(f"Playing {query}", voice_id=self.tts_voice_id)
            except Exception as exc:
                print(f"JARVIS> Failed to play media: {exc}", flush=True)
            return True

        if text.startswith("search ") or text.startswith("google "):
            query = text.replace("search ", "").replace("google ", "").strip()
            # Handle specific user aliases
            if query == "me":
                query = "Tharindu thilakshana de zoysa"
            
            url = f"https://www.google.com/search?q={query}"
            print(f"JARVIS> Searching Google for: {query}", flush=True)
            try:
                webbrowser.open(url)
                if self.voice_enabled:
                     speak(f"Searching for {query}", voice_id=self.tts_voice_id)
            except Exception as exc:
                print(f"JARVIS> Failed to search: {exc}", flush=True)
            return True

        # Direct mission runner without LLM: accepts "mission_run steps=[...]"
        if text.startswith("mission_run"):
            steps_literal = None
            if "[" in text and "]" in text:
                start = text.find("[")
                end = text.rfind("]")
                if start != -1 and end != -1 and end > start:
                    steps_literal = text[start : end + 1]
            try:
                steps = ast.literal_eval(steps_literal) if steps_literal else []
            except Exception as exc:
                print(f"JARVIS> Could not parse mission steps: {exc}", flush=True)
                return True

            if not isinstance(steps, list):
                print("JARVIS> Mission steps must be a list.", flush=True)
                return True

            try:
                runner = MissionRunner(browser=self._get_browser_session())
                result = runner.run(steps)
                summary = result.as_text()
                print(f"JARVIS> Mission complete:\n{summary}", flush=True)
            except MissionError as exc:
                print(f"JARVIS> Mission failed: {exc}", flush=True)
            except Exception as exc:
                print(f"JARVIS> Mission unexpected error: {exc}", flush=True)
            return True

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
                open_app(
                    app_name=chosen_app,
                    allowlist=allowlist,
                    require_confirm=False,  # quick commands should not block on stdin
                    logger=logger,
                )
                print(f"JARVIS> Opening {chosen_app}...", flush=True)
            except Exception as exc:
                print(f"JARVIS> Failed to open {chosen_app}: {exc}", flush=True)
            return True

        return False

    def _handle_heuristic_response(self, user_input: str, long_term: LongTermMemory, short_term: ShortTermMemory) -> bool:
        """Handle common conversational phrases instantly without LLM."""
        text = user_input.strip().lower()
        
        # Butler-style responses
        responses = {
            "hi": "At your service, Sir.",
            "hello": "Hello, Sir. How may I assist you?",
            "hi jarvis": "Greetings, Sir. Standing by.",
            "hello jarvis": "Hello, Sir. I am ready.",
            "hey jarvis": "Yes, Sir?",
            "good morning": "Good morning, Sir.",
            "good evening": "Good evening, Sir.",
            "thank you": "My pleasure, Sir.",
            "thanks": "You are quite welcome, Sir.",
            "who are you": "I am J.A.R.V.I.S., your personal digital butler.",
            "what can you do": "I can control your PC, launch apps, type text, read screens, and manage your schedule, Sir.",
        }

        # Check for exact match or simple containment
        response = responses.get(text)
        if not response:
             # Try partial matches for some keys
             for key, val in responses.items():
                 if text == key: # Exact match preference
                     response = val
                     break
        
        if response:
            print(f"JARVIS> {response}", flush=True)
            if self.voice_enabled:
                speak(response, voice_id=self.tts_voice_id)
            
            # Persist to memory
            short_term.add(response)
            long_term.add_entry(f"User: {user_input}\nJARVIS: {response}", tags=["chat", "heuristic"])
            long_term.save()
            return True

        return False

    def _handle_remember_command(self, user_input: str, long_term: LongTermMemory, short_term: ShortTermMemory) -> bool:
        """Handle explicit memory commands like 'remember that...' or 'memorize...'"""
        text = user_input.strip().lower()
        
        # Check for memory trigger words
        triggers = ["remember that", "remember this", "memorize", "don't forget", "keep in mind"]
        
        for trigger in triggers:
            if text.startswith(trigger):
                # Extract what to remember
                memory_content = user_input[len(trigger):].strip()
                if not memory_content:
                    response = "What would you like me to remember, Sir?"
                else:
                    # Store in long-term memory with special tag
                    long_term.add_entry(memory_content, tags=["user_memory", "important"])
                    long_term.save()
                    response = f"Understood, Sir. I will remember: {memory_content}"
                
                print(f"JARVIS> {response}", flush=True)
                if self.voice_enabled:
                    speak(response, voice_id=self.tts_voice_id)
                
                short_term.add(response)
                return True
        
        return False

    def _handle_identity_query(self, user_input: str, long_term: LongTermMemory, short_term: ShortTermMemory) -> bool:
        """Answer name/identity questions quickly without LLM, using stored memories."""
        text = user_input.strip().lower()
        triggers = ["what is my name", "tell me my name", "who am i", "do you know my name"]
        if not any(trigger in text for trigger in triggers):
            return False

        hits = long_term.search("name", top_k=5)
        found = None
        for item in hits:
            entry = item.get("entry", {})
            txt = entry.get("text", "")
            if not txt:
                continue
            lower = txt.lower()
            if "name" in lower or "call you" in lower:
                found = txt
                break

        if found:
            response = f"You told me your name is: {found}"
        else:
            response = "I don't have your name stored yet. Tell me and I'll remember it."

        print(f"JARVIS> {response}", flush=True)
        if self.voice_enabled:
            speak(response, voice_id=self.tts_voice_id)
        short_term.add(response)
        long_term.add_entry(f"User: {user_input}\nJARVIS: {response}", tags=["chat", "identity"])
        long_term.save()
        return True

    def _check_local_ollama(self) -> bool:
        """Quick health check to see if Ollama is reachable before we rely on it."""
        try:
            import urllib.request

            url = self.local_client.base_url + "/api/tags"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=min(self.local_client.timeout, 5.0)) as resp:
                _ = resp.read()
            return True
        except Exception as exc:
            print(f"[JARVIS] Ollama health check failed: {exc}", flush=True)
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
            if not str(response.text).strip():
                raise RuntimeError("Empty response from LLM")
            try:
                payload = self._parse_json_response(response.text)
            except Exception:
                # If the model responded with plain text, treat it as a normal response.
                text = response.text.strip()
                if text:
                    payload = {
                        "intent": "respond",
                        "action": "respond",
                        "action_input": text,
                        "needs_confirmation": False,
                    }
                else:
                    print("[JARVIS][LLM] Non-JSON response or LLM error, using fallback.", flush=True)
                    payload = {
                        "intent": "unknown",
                        "action": "respond",
                        "action_input": "I need more details or the local model is unavailable. Please clarify or check Ollama.",
                        "needs_confirmation": False,
                    }
        except Exception as e:
            print(f"[JARVIS][LLM] LLM request failed: {e}", flush=True)
            print("[JARVIS][LLM] Using fallback response.", flush=True)
            payload = {
                "intent": "unknown",
                "action": "respond",
                "action_input": "I need more details or the local model is unavailable. Please clarify or check Ollama.",
                "needs_confirmation": False,
            }

        # Heuristic: If action is "respond" but input looks like internal thought, print it but don't fail
        if payload.get("action") == "respond" and (
            "analyz" in str(payload.get("action_input", "")).lower() 
            or "think" in str(payload.get("action_input", "")).lower()
        ):
             print(f"JARVIS (Thinking)> {payload.get('action_input')}", flush=True)
             return Decision(
                intent="thinking",
                action="respond",
                action_input=payload.get("action_input"),
                needs_confirmation=False,
            )

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

        if decision.action == "fetch_url":
            url = self._get_field(decision.action_input, "url")
            if not url:
                return "failed", "Missing URL"
            try:
                resp: HttpResponse = http_get(url)
            except HttpError as exc:
                print(f"JARVIS> Failed to fetch URL: {exc}", flush=True)
                return "failed", str(exc)
            except Exception as exc:  # pragma: no cover - network
                print(f"JARVIS> Error fetching URL: {exc}", flush=True)
                return "failed", str(exc)

            # Show a truncated preview so the model and user can work with it
            preview = resp.content[:2000]
            print(f"JARVIS> [fetched {resp.url} status={resp.status}]\n{preview}", flush=True)
            return "success", None

        if decision.action == "http_post":
            url = self._get_field(decision.action_input, "url")
            payload = decision.action_input if isinstance(decision.action_input, dict) else {}
            if not url:
                return "failed", "Missing URL"
            try:
                resp = http_post_json(url, payload=payload)
            except HttpError as exc:
                print(f"JARVIS> HTTP POST failed: {exc}", flush=True)
                return "failed", str(exc)
            preview = resp.content[:2000]
            print(f"JARVIS> [posted {resp.url} status={resp.status}]\n{preview}", flush=True)
            return "success", None

        if decision.action == "download_file":
            url = self._get_field(decision.action_input, "url")
            path_str = self._get_field(decision.action_input, "path") or "./downloads/file.bin"
            if not url:
                return "failed", "Missing URL"
            try:
                path = download_file(url, Path(path_str))
            except HttpError as exc:
                print(f"JARVIS> Download failed: {exc}", flush=True)
                return "failed", str(exc)
            print(f"JARVIS> Downloaded to {path}", flush=True)
            return "success", None

        if decision.action == "extract_links":
            html = self._get_field(decision.action_input, "html") or ""
            base = self._get_field(decision.action_input, "base")
            links = extract_links(html, base=base)
            print("JARVIS> Links:\n" + "\n".join(links), flush=True)
            return "success", None

        if decision.action == "pdf_text":
            path_str = self._get_field(decision.action_input, "path")
            if not path_str:
                return "failed", "Missing PDF path"
            path = Path(path_str)
            try:
                text = pdf_text(path)
            except DocError as exc:
                print(f"JARVIS> PDF error: {exc}", flush=True)
                return "failed", str(exc)
            print(f"JARVIS> [pdf text]\n{text}", flush=True)
            return "success", None

        if decision.action == "sniff_tokens":
            text = self._get_field(decision.action_input, "text") or ""
            tokens = sniff_verification_tokens(text)
            print("JARVIS> Tokens:\n" + "\n".join(tokens), flush=True)
            return "success", None

        if decision.action == "mission_run":
            steps = []
            if isinstance(decision.action_input, list):
                steps = decision.action_input
            elif isinstance(decision.action_input, dict) and "steps" in decision.action_input:
                steps = decision.action_input.get("steps") or []
            if not isinstance(steps, list):
                return "failed", "Mission steps must be a list"

            try:
                runner = MissionRunner(browser=self._get_browser_session())
                result = runner.run(steps)
                summary = result.as_text()
                print(f"JARVIS> Mission complete:\n{summary}", flush=True)
                return "success", None
            except MissionError as exc:
                print(f"JARVIS> Mission failed: {exc}", flush=True)
                return "failed", str(exc)
            except Exception as exc:
                print(f"JARVIS> Mission unexpected error: {exc}", flush=True)
                return "failed", str(exc)

        if decision.action.startswith("browser_"):
            try:
                browser = self._get_browser_session()
            except Exception as exc:
                print(f"JARVIS> Browser unavailable: {exc}", flush=True)
                return "failed", str(exc)

            try:
                if decision.action == "browser_open":
                    url = self._get_field(decision.action_input, "url")
                    if not url:
                        return "failed", "Missing URL"
                    browser.open(url)
                    print(f"JARVIS> Opened {url}", flush=True)
                    return "success", None

                if decision.action == "browser_fill":
                    selector = self._get_field(decision.action_input, "selector")
                    text = self._get_field(decision.action_input, "text") or ""
                    if not selector:
                        return "failed", "Missing selector"
                    browser.fill(selector, text)
                    print(f"JARVIS> Filled selector {selector}", flush=True)
                    return "success", None

                if decision.action == "browser_click":
                    selector = self._get_field(decision.action_input, "selector")
                    if not selector:
                        return "failed", "Missing selector"
                    browser.click(selector)
                    print(f"JARVIS> Clicked selector {selector}", flush=True)
                    return "success", None

                if decision.action == "browser_submit":
                    selector = self._get_field(decision.action_input, "selector")
                    if not selector:
                        return "failed", "Missing selector"
                    browser.submit(selector)
                    print(f"JARVIS> Submitted selector {selector}", flush=True)
                    return "success", None

                if decision.action == "browser_wait":
                    selector = self._get_field(decision.action_input, "selector")
                    if not selector:
                        return "failed", "Missing selector"
                    browser.wait_for(selector)
                    print(f"JARVIS> Waited for {selector}", flush=True)
                    return "success", None

                if decision.action == "browser_text":
                    selector = self._get_field(decision.action_input, "selector")
                    if not selector:
                        return "failed", "Missing selector"
                    text = browser.text(selector)
                    print(f"JARVIS> [text from {selector}]\n{text}", flush=True)
                    if self.voice_enabled and text:
                        speak(text, voice_id=self.tts_voice_id)
                    return "success", None

                if decision.action == "browser_screenshot":
                    path_str = self._get_field(decision.action_input, "path") or "./logs/browser.png"
                    path = Path(path_str)
                    out_path = browser.screenshot(path)
                    print(f"JARVIS> Screenshot saved to {out_path}", flush=True)
                    return "success", None
            except BrowserError as exc:
                print(f"JARVIS> Browser error: {exc}", flush=True)
                return "failed", str(exc)
            except Exception as exc:
                print(f"JARVIS> Browser unexpected error: {exc}", flush=True)
                return "failed", str(exc)

        if decision.action.startswith("cred_"):
            store = CredentialStore()
            try:
                if decision.action == "cred_save":
                    name = self._get_field(decision.action_input, "name")
                    value = self._get_field(decision.action_input, "value")
                    if not name or value is None:
                        return "failed", "Missing name or value"
                    store.set(name, value)
                    print(f"JARVIS> Stored credential '{name}' (encrypted)", flush=True)
                    return "success", None
                if decision.action == "cred_get":
                    name = self._get_field(decision.action_input, "name")
                    if not name:
                        return "failed", "Missing name"
                    val = store.get(name)
                    if val is None:
                        print(f"JARVIS> No credential found for '{name}'", flush=True)
                        return "failed", "Not found"
                    masked = val[:2] + "***" + val[-2:] if len(val) >= 4 else "***"
                    print(f"JARVIS> Retrieved credential '{name}' (masked): {masked}", flush=True)
                    return "success", None
                if decision.action == "cred_delete":
                    name = self._get_field(decision.action_input, "name")
                    if not name:
                        return "failed", "Missing name"
                    store.delete(name)
                    print(f"JARVIS> Deleted credential '{name}'", flush=True)
                    return "success", None
            except CredentialError as exc:
                print(f"JARVIS> Credential store error: {exc}", flush=True)
                return "failed", str(exc)
            except Exception as exc:
                print(f"JARVIS> Credential unexpected error: {exc}", flush=True)
                return "failed", str(exc)

        if decision.action == "moltbook_post":
            title = self._get_field(decision.action_input, "title")
            content = self._get_field(decision.action_input, "content")
            submolt = self._get_field(decision.action_input, "submolt") or "general"
            if not title or not content:
                return "failed", "Missing title or content for Moltbook post"
            try:
                molt_resp = moltbook_create_post(title=title, content=content, submolt=submolt)
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
        
        # Separate user memories from other memories
        user_memories = []
        other_memories = []
        
        for item in hits:
            entry = item.get("entry", {})
            tags = entry.get("tags", [])
            
            if "user_memory" in tags or "important" in tags:
                user_memories.append(item)
            else:
                other_memories.append(item)
        
        lines = []
        
        # Add user memories first with emphasis
        if user_memories:
            lines.append("IMPORTANT USER MEMORIES (use these to answer questions):")
            for item in user_memories:
                entry = item.get("entry", {})
                text = entry.get("text", "")
                lines.append(f"  * {text}")
        
        # Add other memories
        if other_memories:
            if user_memories:
                lines.append("\nOther relevant context:")
            for item in other_memories:
                entry = item.get("entry", {})
                text = entry.get("text", "")
                score = item.get("score", 0.0)
                lines.append(f"  - (score: {score:.2f}) {text}")
        
        return "\n".join(lines)

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            extracted = self._extract_json_object(text)
            return json.loads(extracted)

    def _extract_json_object(self, text: str) -> str:
        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON object found in response")
        depth = 0
        for idx in range(start, len(text)):
            char = text[idx]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : idx + 1]
        raise ValueError("Unterminated JSON object in response")

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

    def _get_browser_session(self) -> BrowserSession:
        if self.browser_session is not None:
            return self.browser_session

        browser_settings = self.settings.get("browser", {})
        headless = bool(browser_settings.get("headless", True))
        driver_path_val = browser_settings.get("driver_path")
        driver_path = Path(driver_path_val) if driver_path_val else None
        default_timeout = float(browser_settings.get("timeout", 15.0))

        config = BrowserConfig(headless=headless, driver_path=driver_path, default_timeout=default_timeout)
        self.browser_session = BrowserSession(config)
        return self.browser_session
