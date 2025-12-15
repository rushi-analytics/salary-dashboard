from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import json
import requests
import re
from dotenv import load_dotenv

# -------------------------------------------------
# LOAD ENV
# -------------------------------------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("❌ GROQ_API_KEY missing in .env")

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
        return text[:6000] if len(text) > 100 else "Short resume text."
    except Exception:
        return "Resume extraction failed."

# -------------------------------------------------
# GROQ AI ANALYSIS (REAL AI)
# -------------------------------------------------
def groq_analyze(text: str):
    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
You are an ATS Resume & Career Intelligence AI.

Return ONLY valid JSON. No markdown. No explanation.

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
        "model": "llama-3.1-8b-instant",   # ✅ FREE + ACTIVE
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        data = response.json()

        if "choices" not in data:
            return fallback("Groq API error", data)

        content = data["choices"][0]["message"]["content"]

        # Extract JSON safely
        start = content.find("{")
        end = content.rfind("}") + 1
        parsed = json.loads(content[start:end])

        return normalize(parsed)

    except Exception as e:
        return fallback("AI parsing failed", str(e))

# -------------------------------------------------
# NORMALIZE OUTPUT (FRONTEND SAFE)
# -------------------------------------------------
def normalize(d):
    return {
        "ats": int(d.get("ats", 0)),
        "required_skills": d.get("required_skills", []),
        "matched_skills": d.get("matched_skills", []),
        "missing_skills": d.get("missing_skills", []),
        "salary_range": d.get("salary_range", {"min":0,"median":0,"max":0}),
        "salary_distribution": d.get("salary_distribution", {"labels":[],"counts":[]}),
        "demand_score": int(d.get("demand_score", 0)),
        "ai_plan": d.get("ai_plan", {"priority":[],"roadmap":{},"short_note":""}),
        "jobs": d.get("jobs", [])
    }

# -------------------------------------------------
# SAFE FALLBACK (NEVER CRASH UI)
# -------------------------------------------------
def fallback(error, raw):
    return {
        "error": error,
        "raw": raw,
        "ats": 0,
        "required_skills": [],
        "matched_skills": [],
        "missing_skills": [],
        "salary_range": {"min":0,"median":0,"max":0},
        "salary_distribution": {"labels":[],"counts":[]},
        "demand_score": 0,
        "ai_plan": {"priority":[],"roadmap":{},"short_note":""},
        "jobs": []
    }

# -------------------------------------------------
# API ENDPOINT
# -------------------------------------------------
@app.post("/api/ai_full_analysis")
async def analyze(resume: UploadFile = File(...)):
    text = await extract_text(resume)
    return groq_analyze(text)

# -------------------------------------------------
# START SERVER
# -------------------------------------------------
print("🚀 Backend running at http://127.0.0.1:5000")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
