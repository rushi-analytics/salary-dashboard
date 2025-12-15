from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import requests
from dotenv import load_dotenv
import os

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def extract_text(file: UploadFile):
    raw = await file.read()

    try:
        text = raw.decode("utf-8", errors="ignore")
        if len(text.strip()) < 20:
            return "Resume text too short — fallback text."
        return text[:6000]
    except:
        return "Resume extraction failed — fallback text."


def deepseek_analyze(text):
    prompt = f"""
You are an expert ATS & Resume Intelligence AI.
Analyze the resume below and return STRICT JSON ONLY.

Resume:
{text}

Return EXACT JSON with:

{{
  "ats": <0-100>,
  "required_skills": [...],
  "matched_skills": [...],
  "missing_skills": [...],
  "salary_range": {{"min": number, "median": number, "max": number}},
  "salary_distribution": {{"labels": [...], "counts": [...]}},
  "demand_score": <0-100>,
  "ai_plan": {{
      "priority": [...],
      "roadmap": {{
          "<skill>": {{
             "steps": [...],
             "resources": [...]
          }}
      }},
      "short_note": "..."
  }},
  "jobs": [
      {{"title": "...", "company": "...", "location": "..."}}
  ]
}}

Only return JSON. No text outside JSON.
"""

    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }

    response = requests.post(url, headers=headers, json=payload)
    result = response.json()["choices"][0]["message"]["content"]

    try:
        return json.loads(result)
    except:
        return {"error": "AI returned invalid JSON", "raw": result}


@app.post("/api/ai_full_analysis")
async def analyze(resume: UploadFile = File(...)):
    text = await extract_text(resume)
    ai_json = deepseek_analyze(text)
    return ai_json


print("🚀 Backend running at http://127.0.0.1:5000")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
