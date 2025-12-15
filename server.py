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

# Allow frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Extract text
# -----------------------------
async def extract_text(file: UploadFile):
    raw = await file.read()

    try:
        text = raw.decode("utf-8", errors="ignore")
        if len(text.strip()) < 20:
            return "Resume text too short — fallback text."
        return text[:5000]
    except:
        return "Resume extraction failed — fallback used."


# -----------------------------
# DeepSeek R1 Call
# -----------------------------
def deepseek_analyze(text):
    prompt = f"""
You are an ATS + Salary + Skill Analysis AI. 
Read the resume text below and return STRICT JSON ONLY.

Resume:
{text}

Return JSON with exactly these fields:

{{
  "ats": <0-100 score>,
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
IMPORTANT: Return ONLY VALID JSON. No explanations.
    """

    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    response = requests.post(url, headers=headers, json=payload)
    
    raw = response.json()["choices"][0]["message"]["content"]

    try:
        return json.loads(raw)
    except:
        return {"error": "AI returned invalid JSON", "raw": raw}


# -----------------------------
# API Endpoint
# -----------------------------
@app.post("/api/ai_full_analysis")
async def analyze(resume: UploadFile = File(...)):
    text = await extract_text(resume)
    ai_json = deepseek_analyze(text)
    return ai_json


# -----------------------------
# Run server
# -----------------------------
print("🚀 Backend running at http://127.0.0.1:5000")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
