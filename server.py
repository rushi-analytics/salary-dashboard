import os
import io
import requests
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
import docx

# Load env
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY", "")

app = FastAPI(title="Salary Dashboard API Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ Resume Extract ------------------
def extract_text_from_pdf(bytes_data):
    text = ""
    try:
        reader = PdfReader(io.BytesIO(bytes_data))
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        return text
    except:
        return bytes_data.decode("utf-8", errors="ignore")


def extract_text_from_docx(bytes_data):
    try:
        doc = docx.Document(io.BytesIO(bytes_data))
        return "\n".join([p.text for p in doc.paragraphs])
    except:
        return bytes_data.decode("utf-8", errors="ignore")


@app.post("/api/extract_resume")
async def extract_resume(file: UploadFile = File(...)):
    data = await file.read()
    name = file.filename.lower()
    if name.endswith(".pdf"):
        text = extract_text_from_pdf(data)
    elif name.endswith(".docx") or name.endswith(".doc"):
        text = extract_text_from_docx(data)
    else:
        text = data.decode("utf-8", errors="ignore")
    return {"text": text}

# ------------------ DeepSeek Skill Extraction ------------------
@app.post("/api/ai_skills")
async def ai_extract_skills(text: str = Form(...)):
    if not DEEPSEEK_API_KEY:
        return {"error": "DEEPSEEK_API_KEY missing in server."}

    url = "https://api.deepseek.com/v1/chat/completions"
    prompt = f"""
Extract a JSON array of skills from this resume text.
Output ONLY JSON array. No extra text.

Resume:
{text}
"""

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You extract skills from resume text."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 300
    }

    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}

    r = requests.post(url, json=payload, headers=headers)
    try:
        content = r.json()["choices"][0]["message"]["content"]
        return {"skills": content}
    except:
        return {"error": r.text}

# ------------------ DeepSeek AI PLAN (NEW) ------------------
@app.post("/api/ai_plan")
async def ai_plan(
    role: str = Form(...),
    top_skills: str = Form(...),
    user_skills: str = Form(...),
):
    if not DEEPSEEK_API_KEY:
        return {"error": "DEEPSEEK_API_KEY missing in server."}

    prompt = f"""
Create a JSON learning plan.

ROLE: {role}

TOP ROLE SKILLS: {top_skills}

USER SKILLS: {user_skills}

Return JSON with:
- missing: [skills user does not have]
- priority: [top 3 most important skills to learn]
- roadmap: {{
    "<skill>": {{
        "steps": ["step1","step2","step3"],
        "resources": ["url1","url2"]
    }}
}}
- short_note: "one line summary"

Return ONLY JSON.
"""

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You generate skill training plans."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    r = requests.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers)
    try:
        content = r.json()["choices"][0]["message"]["content"]
        return {"plan": content}
    except Exception as e:
        return {"error": str(e), "response": r.text}

# ------------------ JSearch Demand API ------------------
@app.get("/api/job_demand")
async def job_demand(role: str):
    if not JSEARCH_API_KEY:
        return {"error": "JSEARCH_API_KEY missing."}

    url = "https://jsearch.p.rapidapi.com/search"
    params = {"query": role, "page": 1, "num_pages": 1}
    headers = {
        "X-RapidAPI-Key": JSEARCH_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }

    r = requests.get(url, headers=headers, params=params)
    try:
        return r.json()
    except:
        return {"error": r.text}

# ------------------ Run Server ------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)
