from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import requests
from dotenv import load_dotenv
import os

# -------------------------------------------------
# LOAD ENV
# -------------------------------------------------
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    raise RuntimeError("❌ DEEPSEEK_API_KEY missing in .env")

# -------------------------------------------------
# APP INIT
# -------------------------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# RESUME TEXT EXTRACTION (SAFE)
# -------------------------------------------------
async def extract_text(file: UploadFile):
    raw = await file.read()
    try:
        text = raw.decode("utf-8", errors="ignore")
        text = text.strip()
        if len(text) < 50:
            return "Resume content is too short."
        return text[:6000]
    except Exception:
        return "Resume extraction failed."

# -------------------------------------------------
# DEEPSEEK AI ANALYSIS (SAFE + REAL)
# -------------------------------------------------
def deepseek_analyze(text: str):
    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    prompt = f"""
You are an ATS + Career Intelligence AI.

Analyze the resume text and return STRICT JSON ONLY.
No markdown. No explanations.

Required JSON format:
{{
  "ats": number,
  "required_skills": [],
  "matched_skills": [],
  "missing_skills": [],
  "salary_range": {{ "min": number, "median": number, "max": number }},
  "salary_distribution": {{ "labels": [], "counts": [] }},
  "demand_score": number,
  "ai_plan": {{
    "priority": [],
    "roadmap": {{}},
    "short_note": ""
  }},
  "jobs": [{{"title":"","company":"","location":""}}]
}}

Resume text:
{text}
"""

    payload = {
        "model": "deepseek-reasoner",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        data = response.json()

        # 🔒 HANDLE API ERRORS
        if "choices" not in data:
            return {
                "error": "DeepSeek API error",
                "raw": data
            }

        content = data["choices"][0]["message"]["content"]

        # 🔒 PARSE JSON SAFELY
        try:
            return json.loads(content)
        except Exception:
            return {
                "error": "AI returned invalid JSON",
                "raw": content
            }

    except Exception as e:
        return {"error": str(e)}

# -------------------------------------------------
# API ENDPOINT
# -------------------------------------------------
@app.post("/api/ai_full_analysis")
async def analyze(resume: UploadFile = File(...)):
    text = await extract_text(resume)
    ai_json = deepseek_analyze(text)
    return ai_json

# -------------------------------------------------
# START SERVER
# -------------------------------------------------
print("🚀 Backend running at http://127.0.0.1:5000")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
