import cv2
import base64
import json
import logging
import os
from openai import OpenAI

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# --- ROBUST IMPORT LOGIC ---
try:
    from config import OPENAI_API_KEY, VISION_MODEL
except ImportError:
    log.warning("⚠️ Config.py import failed. Falling back to environment variables.")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    VISION_MODEL = "gpt-4o"

# Initialize client
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY not found! Run 'export OPENAI_API_KEY=your_key' in terminal.")

client = OpenAI(api_key=OPENAI_API_KEY)

def frame_to_base64(frame) -> str:
    """Optimizes and converts CV2 frame to Base64 for the LLM."""
    # Tello frames are 720p; we resize to 400px width to save tokens/speed
    height, width = frame.shape[:2]
    new_width = 400
    new_height = int(height * (new_width / width))
    resized = cv2.resize(frame, (new_width, new_height))
    
    _, buffer = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return base64.b64encode(buffer).decode('utf-8')

def analyze_frame(frame, goal: str, telemetry: dict) -> dict:
    """Sends frame and telemetry to LLM and returns a structured dictionary."""
    img_b64 = frame_to_base64(frame)

    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are the vision system of an autonomous Tello drone. Respond ONLY in valid JSON."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_b64}",
                                "detail": "low" 
                            }
                        },
                        {
                            "type": "text",
                            "text": f"Goal: {goal}\nTelemetry: {json.dumps(telemetry)}\n\nReturn JSON: {{'scene': str, 'obstacles': list, 'points_of_interest': list, 'suggestion': str, 'confidence': float}}"
                        }
                    ]
                }
            ],
            max_tokens=400
        )

        content = response.choices[0].message.content.strip()
        
        # Guard against markdown backticks
        if content.startswith("```"):
            content = content.split("json")[-1].replace("```", "").strip()
            
        return json.loads(content)

    except Exception as e:
        log.error(f"Vision Analysis Failed: {e}")
        return {
            "scene": "error",
            "obstacles": [],
            "points_of_interest": [],
            "suggestion": "hover",
            "confidence": 0.0
        }