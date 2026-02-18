J.A.R.V.I.S — Autonomous Triple-Brain AI System

J.A.R.V.I.S (Just A Rather Very Intelligent System) is a next-generation local autonomous AI agent engineered from scratch to operate as a real computer-controlling assistant — inspired by the AI from Iron Man.
Unlike typical assistants, J.A.R.V.I.S is designed as a true agent system capable of reasoning, planning, acting, learning from experience, and executing real-world tasks on your machine.
Built from scratch using Python, offline AI models, and system-level automation tools, this project demonstrates a real-world implementation of a JARVIS-class assistant running entirely on your own machine.
________________________________________
🧠 TRIPLE-BRAIN ARCHITECTURE
J.A.R.V.I.S uses a three-layer intelligence system that dynamically selects the best brain depending on context, privacy needs, and connectivity.
🧊 Brain 1 — Offline Core (Privacy Mode)
Powered by local LLM via Ollama using Mistral.
✔ Works fully offline
✔ No data leaves your machine
✔ Fast local reasoning
✔ Used for sensitive tasks and system control
This enables J.A.R.V.I.S to function even without internet access.
________________________________________
⚡ Brain 2 — High-Speed Online Intelligence
Powered by the Groq API.
✔ Ultra-fast inference
✔ Low-latency responses
✔ Used for complex reasoning when speed matters
________________________________________
🌐 Brain 3 — Advanced Cloud Intelligence
Powered by OpenAI APIs.
✔ Advanced reasoning
✔ Deep knowledge
✔ Complex problem solving
✔ Creative tasks
________________________________________
🧠 Smart Brain Switching
J.A.R.V.I.S can dynamically choose:
•	Offline mode for privacy-critical operations
•	Groq mode for speed
•	OpenAI mode for intelligence
This creates a resilient hybrid AI system.
________________________________________
🎤 HUMAN-LEVEL INTERACTION
Voice Interface
•	Offline STT via Vosk
•	TTS via pyttsx3
•	Push-to-talk control
•	Console fallback
________________________________________
🖥️ FULL COMPUTER CONTROL
J.A.R.V.I.S acts as a digital operator:
✔ Launches and controls applications
✔ Mouse & keyboard automation
✔ Process management
✔ File operations
✔ System monitoring
________________________________________
👁️ SCREEN AWARENESS
Using OCR via Tesseract, J.A.R.V.I.S can:
•	Read visible screen text
•	Understand context
•	Interact with UI elements
________________________________________
🌐 AUTONOMOUS WEB AGENT
J.A.R.V.I.S can:
✔ Visit websites
✔ Fill forms
✔ Perform signup processes
✔ Send requests
✔ Extract information
________________________________________
🤖 MOLTBOOK AGENT INTEGRATION
Dedicated agent tools for the Moltbook ecosystem:
•	Automated interactions
•	Posting & engagement
•	Feed operations
•	Registry skills
________________________________________
🧠 EXPERIENCE-BASED LEARNING
J.A.R.V.I.S improves over time using:
•	Action logs
•	Reflection
•	Skill memory
•	Lessons learned
It becomes smarter through experience — without retraining.
________________________________________
🔒 SAFETY SYSTEM
•	Kill-switch commands
•	App allowlists
•	Confirmation prompts
•	Secure boundaries
•	Full audit logs
________________________________________
🧱 BUILT FROM SCRATCH
Designed and implemented end-to-end:
•	Agent architecture
•	Planner
•	Memory system
•	Tool framework
•	Safety layer
•	Voice interface
•	Automation engine
________________________________________
🧪 MY TECHNICAL REVIEW OF THIS PROJECT
This project demonstrates advanced understanding of:
•	Autonomous agent design
•	Tool-use architectures
•	Hybrid AI deployment
•	Offline AI systems
•	Safety-constrained automation
The triple-brain approach is particularly strong because it balances:
Privacy ↔ Speed ↔ Intelligence
This is closer to real future personal AI systems than most hobby assistants.
________________________________________
⚠️ REALITY VS FICTION
While inspired by cinematic AI:
J.A.R.V.I.S is an advanced real-world assistant — not a fictional omnipotent AI.
________________________________________

▶️ How to Start J.A.R.V.I.S (Windows Setup Guide)
This guide walks you through running your local J.A.R.V.I.S AI agent on Windows using offline and online brains (Ollama, Groq, OpenAI), voice control, and vision capabilities.
________________________________________
🧩 Prerequisites
Ensure the following are installed:
•	Windows 10/11
•	Python 3.10 or higher
•	VS Code
•	Internet connection (only required for initial setup)
________________________________________
📂 1. Clone the Repository
git clone https://github.com/TharinduThilakshana0thildezo/J.A.R.V.I.S.git
cd J.A.R.V.I.S
Open the folder in VS Code.
________________________________________
🧪 2. Create & Activate Virtual Environment
python -m venv .venv
.venv\Scripts\activate
________________________________________
📦 3. Install Python Dependencies
pip install pyautogui psutil pywinauto keyboard vosk sounddevice pyttsx3 mss pillow pytesseract pytest pyyaml requests
________________________________________
🧠 4. Install Offline Brain (Ollama + Mistral)
J.A.R.V.I.S offline mode uses a local LLM via Ollama.
Download Ollama:
👉 https://ollama.com/download
Verify installation:
ollama --version
Pull the local model:
ollama pull mistral
Test:
ollama run mistral "Hello from local JARVIS"
________________________________________
🎤 5. Setup Voice Recognition (Vosk)
Download a Vosk model:
👉 https://alphacephei.com/vosk/models
Extract to:
jarvis_ai/models/vosk-model-small-en-us-0.15
________________________________________
👁️ 6. Install OCR Engine (Screen Awareness)
Download Tesseract OCR:
👉 https://github.com/UB-Mannheim/tesseract/wiki
Ensure it is added to PATH
(or configure path in settings)
________________________________________
⚙️ 7. Configure Settings
Open:
jarvis_ai/config/settings.yaml
Configure Triple-Brain System
Offline Brain
ollama.base_url: http://localhost:11434
ollama.model: mistral
Online Brains
Add your API keys:
groq.api_key: YOUR_GROQ_API_KEY
openai.api_key: YOUR_OPENAI_API_KEY
________________________________________
Configure Voice
voice.enabled: true
voice.stt.model_path: jarvis_ai/models/vosk-model-small-en-us-0.15
voice.stt.push_to_talk_key: right ctrl
________________________________________
Configure Vision
vision.ocr.enabled: true
________________________________________
Safety Controls
safety.allowlist_apps: [list of trusted apps]
safety.kill_switch_commands: ["STOP", "KILL JARVIS"]
________________________________________
🚀 8. Run J.A.R.V.I.S
python jarvis_ai\main.py
If successful, J.A.R.V.I.S will initialize:
•	Brain modules
•	Voice interface
•	Memory system
•	Tool framework
________________________________________
🎤 9. Using Voice Commands
Hold Right Ctrl to speak
Release to submit



▶️ How to Start J.A.R.V.I.S (Windows Setup Guide)
This guide walks you through running your local J.A.R.V.I.S AI agent on Windows using offline and online brains (Ollama, Groq, OpenAI), voice control, and vision capabilities.
________________________________________
🧩 Prerequisites
Ensure the following are installed:
•	Windows 10/11
•	Python 3.10 or higher
•	VS Code
•	Internet connection (only required for initial setup)
________________________________________
📂 1. Clone the Repository
git clone https://github.com/TharinduThilakshana0thildezo/J.A.R.V.I.S.git
cd J.A.R.V.I.S
Open the folder in VS Code.
________________________________________
🧪 2. Create & Activate Virtual Environment
python -m venv .venv
.venv\Scripts\activate
________________________________________
📦 3. Install Python Dependencies
pip install pyautogui psutil pywinauto keyboard vosk sounddevice pyttsx3 mss pillow pytesseract pytest pyyaml requests
________________________________________
🧠 4. Install Offline Brain (Ollama + Mistral)
J.A.R.V.I.S offline mode uses a local LLM via Ollama.
Download Ollama:
👉 https://ollama.com/download
Verify installation:
ollama --version
Pull the local model:
ollama pull mistral
Test:
ollama run mistral "Hello from local JARVIS"
________________________________________
🎤 5. Setup Voice Recognition (Vosk)
Download a Vosk model:
👉 https://alphacephei.com/vosk/models
Extract to:
jarvis_ai/models/vosk-model-small-en-us-0.15
________________________________________
👁️ 6. Install OCR Engine (Screen Awareness)
Download Tesseract OCR:
👉 https://github.com/UB-Mannheim/tesseract/wiki
Ensure it is added to PATH
(or configure path in settings)
________________________________________
⚙️ 7. Configure Settings
Open:
jarvis_ai/config/settings.yaml
Configure Triple-Brain System
Offline Brain
ollama.base_url: http://localhost:11434
ollama.model: mistral
Online Brains
Add your API keys:
groq.api_key: YOUR_GROQ_API_KEY
openai.api_key: YOUR_OPENAI_API_KEY
________________________________________
Configure Voice
voice.enabled: true
voice.stt.model_path: jarvis_ai/models/vosk-model-small-en-us-0.15
voice.stt.push_to_talk_key: right ctrl
________________________________________
Configure Vision
vision.ocr.enabled: true
________________________________________
Safety Controls
safety.allowlist_apps: [list of trusted apps]
safety.kill_switch_commands: ["STOP", "KILL JARVIS"]
________________________________________
🚀 8. Run J.A.R.V.I.S
python jarvis_ai\main.py
If successful, J.A.R.V.I.S will initialize:
•	Brain modules
•	Voice interface
•	Memory system
•	Tool framework
________________________________________
🎤 9. Using Voice Commands
Hold Right Ctrl to speak
Release to submit

📩 CONTACT
Interested in architecture, implementation, or collaboration?
👉 Reach out directly.

