import os
import json
import uvicorn
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from PyPDF2 import PdfReader
import docx

load_dotenv()

DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# EXTRACT TEXT FROM PDF/DOCX
# -----------------------------
def extract_text(file_bytes, filename):
    name = filename.lower()

    # PDF
    if name.endswith(".pdf"):
        try:
            reader = PdfReader(file_bytes)
            text = ""
            for page in reader.pages:
                t = page.extract_text() or ""
                text += t + "\n"
            return text
        except:
            pass

    # DOCX
    if name.endswith(".docx"):
        try:
            doc_file = docx.Document(file_bytes)
            return "\n".join([p.text for p in doc_file.paragraphs])
        except:
            pass

    # TXT fallback
    try:
        return file_bytes.read().decode("utf-8", errors="ignore")
    except:
        return ""

# -----------------------------
# CALL DEEPSEEK AI
# -----------------------------
def deepseek(prompt):
    url = "https://api.deepseek.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json"
    }

    body = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are an expert ATS scanner and resume reviewer."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 700
    }

    r = requests.post(url, json=body, headers=headers)
    try:
        return r.json()["choices"][0]["message"]["content"]
    except:
        return "AI response error"

# -----------------------------
# MAIN ENDPOINT — FULL ANALYSIS
# -----------------------------
@app.post("/api/ai_full_analysis")
async def analyze(resume: UploadFile = File(...)):
    raw = await resume.read()
    text = extract_text(raw, resume.filename)

    if len(text) < 30:
        return {"error": "Resume text could not be extracted."}

    # ---------------- AI REQUEST ----------------
    prompt = f"""
    Analyze this resume deeply.

    RESUME TEXT:
    {text}

    Generate a JSON response EXACTLY in this structure:

    {{
      "ats_score": number 0-100,
      "top_skills": ["skill1","skill2",...],
      "missing_skills": ["skill1","skill2",...],
      "ai_summary": "Short AI-written summary of resume",
      "recommendations": ["fix bullet points", "add achievements", ...],
      "skill_roadmap": {{
          "priority": ["skill1","skill2"],
          "steps": ["step1","step2"]
      }}
    }}
    Only return JSON. No explanation.
    """

    ai_raw = deepseek(prompt)

    # Try parsing JSON
    try:
        ai_json = json.loads(ai_raw)
    except:
        ai_json = {"error": "AI returned invalid JSON", "raw": ai_raw}

    return ai_json

# -----------------------------
# START BACKEND
# -----------------------------
if __name__ == "__main__":
    print("🚀 Backend running at http://127.0.0.1:5000")
    uvicorn.run(app, host="127.0.0.1", port=5000)
