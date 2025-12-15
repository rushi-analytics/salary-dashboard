# server.py
import os
import json
import tempfile
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
from docx import Document
import uvicorn

app = FastAPI()

# Allow CORS for frontend (localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------
def extract_text_from_pdf(path):
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(path):
    doc = Document(path)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_text(file: UploadFile):
    suffix = file.filename.lower()

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    if suffix.endswith(".pdf"):
        return extract_text_from_pdf(tmp_path)
    elif suffix.endswith(".docx"):
        return extract_text_from_docx(tmp_path)
    elif suffix.endswith(".txt"):
        with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    else:
        return ""

# ---------------------------------------------------------
#  ATS SCORE LOGIC
# ---------------------------------------------------------
def calculate_ats_score(resume_text, jd_text):
    resume_words = resume_text.lower().split()
    jd_words = jd_text.lower().split()

    resume_set = set(resume_words)
    jd_set = set(jd_words)

    matched = resume_set.intersection(jd_set)
    missing = jd_set - resume_set

    required_count = len(jd_set)
    matched_count = len(matched)

    score = int((matched_count / required_count) * 100) if required_count > 0 else 0

    return {
        "ats_score": score,
        "matched_skills": list(matched)[:20],
        "missing_skills": list(missing)[:20]
    }

# ---------------------------------------------------------
# Main API: Resume + JD → Full AI Insight
# ---------------------------------------------------------
@app.post("/api/full_analysis")
async def full_analysis(resume: UploadFile = File(...), jd: UploadFile = File(...)):
    resume_text = extract_text(resume)
    jd_text = extract_text(jd)

    ats_result = calculate_ats_score(resume_text, jd_text)

    # SIMPLE STATIC SAMPLE — replace with your AI logic later
    salary_range = {"min": 300000, "median": 450000, "max": 1200000}
    distribution = {
        "labels": ["3L", "5L", "7L", "9L", "11L"],
        "counts": [3, 6, 5, 3, 2]
    }

    ai_learning_plan = {
        "priority": ["python", "sql", "excel"],
        "roadmap": {
            "python": {"steps": ["Basics", "Loops", "Projects"], "resources": ["youtube", "coursera"]},
            "sql": {"steps": ["DDL", "DML", "Joins"], "resources": ["youtube", "coursera"]},
        }
    }

    return {
        "resume_text": resume_text[:1500],
        "jd_text": jd_text[:1500],
        "salary_range": salary_range,
        "salary_distribution": distribution,
        "ats": ats_result,
        "ai_plan": ai_learning_plan,
        "jobs": [
            {"title": "Data Analyst", "company": "ABC Corp", "location": "Pune"},
            {"title": "Business Analyst", "company": "XYZ Ltd", "location": "Remote"}
        ]
    }

# ---------------------------------------------------------

print("🚀 Backend running at http://127.0.0.1:5000")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
