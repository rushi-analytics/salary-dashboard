# server.py
# Small FastAPI proxy to:
#  - extract text from uploaded resume (pdf/docx/txt)
#  - call an AI endpoint (DeepSeek recommended in your list)
#  - call JSearch (jobs) for demand data
#
# Usage: python server.py
# Backend will run on http://127.0.0.1:5000

import os
import io
import requests
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
import docx

# optionally load environment variables from .env if you install python-dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY", "")

app = FastAPI(title="Salary Dashboard API Proxy")

# allow requests from your local front-end (or any origin during dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # in prod, set to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------ helpers: extract resume text ------
def extract_text_from_pdf(file_bytes: bytes) -> str:
    text = ""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception:
        # fallback
        try:
            text = file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            text = ""
    return text

def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception:
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""

# ------ endpoint: extract resume text ------
@app.post("/api/extract_resume")
async def extract_resume(file: UploadFile = File(...)):
    data = await file.read()
    filename = (file.filename or "").lower()
    if filename.endswith(".pdf"):
        text = extract_text_from_pdf(data)
    elif filename.endswith(".docx") or filename.endswith(".doc"):
        text = extract_text_from_docx(data)
    else:
        # txt or fallback
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = ""
    return {"text": text}

# ------ endpoint: AI skills recommendation (DeepSeek example) ------
@app.post("/api/ai_skills")
async def ai_skills(text: str = Form(...)):
    """
    POST form with field 'text' (resume text).
    Returns AI suggestions (string). Uses DeepSeek as example.
    """
    if not DEEPSEEK_API_KEY:
        return {"error": "DEEPSEEK_API_KEY not configured on server."}

    url = "https://api.deepseek.com/v1/chat/completions"
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Extract top skills and recommend missing skills."},
            {"role": "user", "content": f"Resume text:\n\n{text}\n\nReply with a short JSON-like list of top skills and recommended skills."}
        ],
        "max_tokens": 400
    }
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    try:
        j = resp.json()
        ai_text = j.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        ai_text = resp.text
    return {"ai_skills": ai_text, "status_code": resp.status_code}

# ------ endpoint: job demand (JSearch example) ------
@app.get("/api/job_demand")
async def job_demand(role: str):
    """
    Example GET: /api/job_demand?role=Data%20Analyst
    Uses JSearch RapidAPI (replace with your chosen job API).
    """
    if not JSEARCH_API_KEY:
        return {"error": "JSEARCH_API_KEY not configured on server."}

    url = "https://jsearch.p.rapidapi.com/search"
    params = {"query": role, "page": 1, "num_pages": 1}
    headers = {
        "X-RapidAPI-Key": JSEARCH_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    resp = requests.get(url, headers=headers, params=params, timeout=20)
    try:
        return resp.json()
    except Exception:
        return {"status_code": resp.status_code, "text": resp.text}

# Run with: python server.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")
