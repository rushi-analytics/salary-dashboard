from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import requests
from dotenv import load_dotenv
import os
import re

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
# RESUME TEXT EXTRACTION (ROBUST)
# -------------------------------------------------
async def extract_text(file: UploadFile):
    raw = await file.read()

    try:
        text = raw.decode("utf-8", errors="ignore")
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) < 100:
            return "Resume content is too short or unreadable."

        return text[:6000]

    except Exception:
        return "Resume extraction failed."

# -------------------------------------------------
# DEEPSEEK AI ANALYSIS (PRODUCTION SAFE)
# -------------------------------------------------
def deepseek_analyze(text: str):
    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    prompt = f"""
You are an ATS Resume & Career Intelligence AI.

CRITICAL RULES:
- Return ONLY valid JSON
- No markdown
- No explanations
- No text outside JSON

JSON FORMAT:
{{
  "ats": 0,
  "required_skills": [],
  "matched_skills": [],
  "missing_skills": [],
  "salary_range": {{ "min": 0, "median": 0, "max": 0 }},
  "salary_distribution": {{ "labels": [], "counts": [] }},
  "demand_score": 0,
  "ai_plan": {{
    "priority": [],
    "roadmap": {{}},
    "short_note": ""
  }},
  "jobs": [
    {{"title":"","company":"","location":""}}
  ]
}}

Resume:
{text}
"""

    payload = {
        "model": "deepseek-chat",   # ✅ stable model
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )

        data = response.json()

        # ----------------------------------
        # HANDLE API FAILURE
        # ----------------------------------
        if "choices" not in data:
            return safe_fallback("DeepSeek API error", data)

        content = data["choices"][0]["message"]["content"]

        # ----------------------------------
        # EXTRACT JSON SAFELY (IMPORTANT)
        # ----------------------------------
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            clean_json = content[start:end]

            parsed = json.loads(clean_json)
            return normalize_output(parsed)

        except Exception:
            return safe_fallback("AI returned invalid JSON", content)

    except Exception as e:
        return safe_fallback("Request failed", str(e))

# -------------------------------------------------
# NORMALIZE OUTPUT (NEVER BREAK FRONTEND)
# -------------------------------------------------
def normalize_output(data: dict):
    return {
        "ats": int(data.get("ats", 0)),
        "required_skills": data.get("required_skills", []),
        "matched_skills": data.get("matched_skills", []),
        "missing_skills": data.get("missing_skills", []),
        "salary_range": {
            "min": data.get("salary_range", {}).get("min", 0),
            "median": data.get("salary_range", {}).get("median", 0),
            "max": data.get("salary_range", {}).get("max", 0),
        },
        "salary_distribution": data.get(
            "salary_distribution",
            {"labels": [], "counts": []}
        ),
        "demand_score": int(data.get("demand_score", 0)),
        "ai_plan": data.get(
            "ai_plan",
            {"priority": [], "roadmap": {}, "short_note": ""}
        ),
        "jobs": data.get("jobs", []),
    }

# -------------------------------------------------
# FALLBACK RESPONSE (UI NEVER CRASHES)
# -------------------------------------------------
def safe_fallback(error, raw):
    return {
        "error": error,
        "raw": raw,
        "ats": 0,
        "required_skills": [],
        "matched_skills": [],
        "missing_skills": [],
        "salary_range": {"min": 0, "median": 0, "max": 0},
        "salary_distribution": {"labels": [], "counts": []},
        "demand_score": 0,
        "ai_plan": {"priority": [], "roadmap": {}, "short_note": ""},
        "jobs": []
    }

# -------------------------------------------------
# API ENDPOINT
# -------------------------------------------------
@app.post("/api/ai_full_analysis")
async def analyze(resume: UploadFile = File(...)):
    text = await extract_text(resume)
    return deepseek_analyze(text)

# -------------------------------------------------
# START SERVER
# -------------------------------------------------
print("🚀 Backend running at http://127.0.0.1:5000")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
