import sys
sys.path.insert(0, "e:/Education/J.A.R.V.I.S")

from jarvis_ai.brain.llm import LLMClient

# Test Groq connection with User-Agent fix
client = LLMClient(
    base_url="http://localhost:11434",
    model="llama-3.3-70b-versatile",
    timeout=30.0,
    provider="groq",
    api_key="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"
)

print("Testing Groq connection with User-Agent fix...")
try:
    response = client.generate(
        prompt="Say 'Hello Sir, I am JARVIS and I am now fully operational!' in a butler-like manner.",
        system="You are JARVIS, a loyal AI butler."
    )
    print("\n✓ SUCCESS! Groq is working!\n")
    print(f"JARVIS: {response.text}\n")
    print("J.A.R.V.I.S is now ready to use!")
except Exception as e:
    print(f"\n✗ ERROR: {e}\n")
