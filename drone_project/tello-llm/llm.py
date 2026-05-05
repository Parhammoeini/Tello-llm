import json
import os
from openai import OpenAI

print("✅ llm.py is loading")

# --- SAFE IMPORT ---
try:
    from config import OPENAI_API_KEY, PLANNER_MODEL
except Exception:
    print("⚠️ config.py failed, using env vars")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    PLANNER_MODEL = "gpt-4o-mini"

if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY missing")

#client = OpenAI(api_key=OPENAI_API_KEY)
client = OpenAI(
    base_url='http://localhost:11434/v1',
    api_key='ollama', 
)

SYSTEM_PROMPT = """
You are an autonomous drone pilot. Commands are RELATIVE to current position.

Available commands:
  {"cmd": "takeoff"}
  {"cmd": "land"}
  {"cmd": "move", "direction": "forward|back|left|right|up|down", "cm": int}
  {"cmd": "rotate", "direction": "cw|ccw", "degrees": int}
  {"cmd": "hover", "seconds": float}
  {"cmd": "flip", "direction": "l|r|f|b"}
  {"cmd": "capture_and_analyze"}

Rules:
1. Output ONLY a valid JSON object: {"commands": [...]}.
2. Max 5 commands per response.
3. Battery < 15% → Output {"cmd": "land"} immediately.
4. If Vision confidence < 0.5 → Hover, then capture_and_analyze.
5. If target not visible → Rotate in 45-degree increments to scan.
6. Keep movements between 20-50cm for precision.
"""

def plan_next_commands(goal: str, telemetry: dict, vision: dict) -> list:
    payload = {
        "goal": goal,
        "telemetry": telemetry,
        "vision": vision
    }

    print("\n🧾 === LLM INPUT ===")
    print(json.dumps(payload, indent=2))

    response = client.chat.completions.create(
        model="llama3.2:1b",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""Mission: {goal}
Telemetry: {json.dumps(telemetry)}
Vision: {json.dumps(vision)}

Return: {{"commands": [...]}}"""
            }
        ],
        max_tokens=300
    )

    content = response.choices[0].message.content

    print("\n🤖 === LLM RAW RESPONSE ===")
    print(content)

    parsed = json.loads(content)
    commands = parsed.get("commands", parsed)

    print("\n📦 === PARSED COMMANDS ===")
    print(json.dumps(commands, indent=2))

    return commands