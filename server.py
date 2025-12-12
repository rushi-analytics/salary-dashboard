from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import re

app = FastAPI()

# CORS so frontend can call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Helper functions
# -----------------------------
def extract_text_from_resume(file_bytes: bytes):
    """Extract simple text from PDF/DOCX/TXT"""
    try:
        return file_bytes.decode("utf-8", errors="ignore")
    except:
        return ""

def find_skills(text):
    skill_keywords = [
        "python","sql","excel","power bi","tableau","aws","azure","gcp",
        "docker","kubernetes","pandas","numpy","machine learning","data analysis",
    ]
    found = []
    low = text.lower()
    for s in skill_keywords:
        if s in low:
            found.append(s)
    return list(set(found))

def compute_salary_stats():
    """Synthetic salary stats since no CSV is uploaded"""
    return {
        "min": 300000,
        "median": 650000,
        "max": 1200000
    }

def compute_salary_distribution():
    return {
        "labels": ["3-5L","5-7L","7-9L","9-12L"],
        "counts": [4, 8, 5, 2]
    }

# -----------------------------
# MAIN ROUTE CALLED BY script.js
# -----------------------------
@app.post("/api/ai_full_analysis")
async def analyze_resume(file: UploadFile = File(...)):
    # read file
    resume_bytes = await file.read()
    text = extract_text_from_resume(resume_bytes)

    # parse skills
    extracted = find_skills(text)

    # example required skills
    required = ["python","sql","excel","tableau","power bi"]
    matched = [s for s in required if s in extracted]
    missing = [s for s in required if s not in extracted]

    # resume fit score
    score = int((len(matched) / len(required)) * 100)

    # salary
    salary_stats = compute_salary_stats()

    # demand synthetic
    demand_score = 75

    # AI learning plan (fake but structured)
    ai_plan = {
        "priority": missing[:3],
        "roadmap": {
            s: {
                "steps": ["Learn basics", "Do projects", "Add to resume"],
                "resources": ["https://youtube.com", "https://coursera.org"]
            }
            for s in missing
        },
        "short_note": "Improve missing skills to increase job match rate."
    }

    # synthetic job postings
    jobs = [
        {"title": "Data Analyst", "company": "ABC Corp", "location": "India"},
        {"title": "Business Analyst", "company": "XYZ Pvt Ltd", "location": "Remote"},
    ]

    # send response
    return {
        "salary_range": salary_stats,
        "resume_fit_score": score,
        "components": {
            "skillComponent": score,
            "demandComponent": 15,
            "salaryComponent": 10
        },
        "required_skills": required,
        "matched_skills": matched,
        "missing_skills": missing,
        "salary_distribution": compute_salary_distribution(),
        "demand_score": demand_score,
        "ai_plan": ai_plan,
        "jobs": jobs,
        "raw_text": text[:500]
    }

# -----------------------------
# Run server
# -----------------------------
if __name__ == "__main__":
    print("🚀 Starting Backend on http://127.0.0.1:5000 ...")
    uvicorn.run(app, host="127.0.0.1", port=5000)
