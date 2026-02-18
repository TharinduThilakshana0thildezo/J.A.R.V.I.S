🤖 J.A.R.V.I.S — Autonomous Triple-Brain AI Agent
A Real Local AI System Inspired by Iron Man

J.A.R.V.I.S (Just A Rather Very Intelligent System) is a next-generation autonomous AI agent engineered to function as a real computer-controlling assistant — not a chatbot, not a wrapper, but a true agentic system capable of reasoning, planning, acting, and learning on your machine.

⚡ Built from scratch using Python, offline models, and system automation
🧠 Runs locally with optional cloud intelligence
🔐 Privacy-first architecture
🖥️ Full computer control capabilities

🏆 PROJECT STATUS — ELITE AGENT SYSTEM

✔ Autonomous Agent Architecture
✔ Triple-Brain Hybrid Intelligence
✔ Offline Operation Capability
✔ Voice + Vision Interface
✔ Real System Control
✔ Experience-Based Learning

This is closer to a real personal AI operating system than a typical assistant.

🧠 TRIPLE-BRAIN ARCHITECTURE

A dynamic intelligence routing system that selects the optimal brain based on task requirements.

Brain	Purpose	Technology	When Used
🧊 Offline Core	Privacy & Control	Ollama + Mistral	Sensitive/system tasks
⚡ Speed Brain	Ultra-Fast Reasoning	Groq API	Time-critical queries
🌐 Intelligence Brain	Deep Reasoning	OpenAI API	Complex/creative work
🧠 Smart Brain Switching

J.A.R.V.I.S automatically balancesڍ selects:

🔒 Offline → Privacy
⚡ Groq → Speed
🧠 OpenAI → Intelligence

Result: A resilient hybrid AI system balancing
Privacy ↔ Speed ↔ Intelligence

🎤 HUMAN-LEVEL INTERFACE
🎙️ Voice System

✔ Offline Speech Recognition (Vosk)
✔ Text-to-Speech (pyttsx3)
✔ Push-to-Talk
✔ Console fallback

🖥️ FULL COMPUTER CONTROL

J.A.R.V.I.S acts as a digital operator

✔ Launch & control applications
✔ Mouse & keyboard automation
✔ File system operations
✔ Process management
✔ System monitoring

👁️ SCREEN AWARENESS (VISION)

OCR via Tesseract enables:

📖 Reading visible text
🧠 Context understanding
🖱️ UI interaction

🌐 AUTONOMOUS WEB AGENT

J.A.R.V.I.S can:

🌍 Navigate websites
📝 Fill forms
📨 Send requests
🔎 Extract data
🆕 Complete workflows

🤖 EXPERIENCE-BASED LEARNING

Improves over time using:

📜 Action logs
🧠 Skill memory
🤔 Reflection
📘 Lessons learned

Learns without retraining models

🔒 SAFETY SYSTEM

🛑 Kill switch commands
📋 App allowlists
❗ Confirmation prompts
🔐 Secure boundaries
📑 Audit logs

🧱 BUILT FROM SCRATCH

End-to-end custom implementation:

🧠 Agent architecture
🗺️ Planner
💾 Memory system
🧰 Tool framework
🎤 Voice interface
⚙️ Automation engine
🔐 Safety layer

▶️ QUICK START — WINDOWS SETUP
🧩 Prerequisites

Windows 10/11

Python 3.10+

VS Code

Internet (initial setup only)

📥 1. Clone Repository
git clone https://github.com/TharinduThilakshana0thildezo/J.A.R.V.I.S.git
cd J.A.R.V.I.S

🧪 2. Virtual Environment
python -m venv .venv
.venv\Scripts\activate

📦 3. Install Dependencies
pip install pyautogui psutil pywinauto keyboard vosk sounddevice pyttsx3 mss pillow pytesseract pytest pyyaml requests

🧠 4. Offline Brain Setup (Ollama + Mistral)

Download Ollama → https://ollama.com/download

ollama --version
ollama pull mistral
ollama run mistral "Hello from local JARVIS"

🎤 5. Voice Recognition (Vosk)

Download model → https://alphacephei.com/vosk/models

Extract to:

jarvis_ai/models/vosk-model-small-en-us-0.15

👁️ 6. OCR Engine (Tesseract)

Download → https://github.com/UB-Mannheim/tesseract/wiki

Add to PATH.

⚙️ 7. Configure Settings

Open:

jarvis_ai/config/settings.yaml

🧠 Triple Brain
ollama.base_url: http://localhost:11434
ollama.model: mistral

groq.api_key: YOUR_GROQ_API_KEY
openai.api_key: YOUR_OPENAI_API_KEY

🎤 Voice
voice.enabled: true
voice.stt.model_path: jarvis_ai/models/vosk-model-small-en-us-0.15
voice.stt.push_to_talk_key: right ctrl

👁️ Vision
vision.ocr.enabled: true

🔒 Safety
safety.allowlist_apps: [trusted apps]
safety.kill_switch_commands: ["STOP", "KILL JARVIS"]

🚀 8. Run J.A.R.V.I.S
python jarvis_ai\main.py


Initialization includes:

🧠 Brain modules
🎤 Voice interface
💾 Memory system
🧰 Tool framework

🎤 9. Voice Usage

Hold Right Ctrl → Speak
Release → Execute

🧪 TECHNICAL SIGNIFICANCE

This project demonstrates:

🤖 Autonomous agent engineering
🧰 Tool-use architectures
🌐 Hybrid AI deployment
🧊 Offline AI systems
🔒 Safety-constrained automation

Represents the direction of future personal AI systems.

⚠️ REALITY VS FICTION

Inspired by cinematic AI — but this is a real working system, not fictional omnipotence.

📊 ROADMAP

Planned enhancements:

Wake-word activation

Long-term memory graph

Multi-agent coordination

Visual UI

Plugin ecosystem

Self-improvement loop

📩 CONTACT & COLLABORATION

Interested in architecture, research, or collaboration?

Reach out directly.

⭐ WHY THIS PROJECT STANDS OUT

Most assistants are:

❌ Chat interfaces
❌ Cloud-dependent
❌ Passive

J.A.R.V.I.S is:

✅ Autonomous
✅ Local-first
✅ Action-capable
✅ Hybrid intelligent