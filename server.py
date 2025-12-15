from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json

app = FastAPI()

# -----------------------------------------
# CORS FIX (CRITICAL FOR FRONTEND)
# -----------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # allow all (local dev)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------
# HEALTH CHECK (SO YOU KNOW SERVER IS RUNNING)
# -----------------------------------------
@app.get("/health")
def health():
    return {"status": "running"}

# -----------------------------------------
# SAFE RESUME TEXT EXTRACTOR
# -----------------------------------------
async def extract_text(file: UploadFile):
    try:
        raw = await file.read()
        text = raw.decode("utf-8", errors="ignore")
        if len(text.strip()) < 20:
            return "Resume text extracted (mocked)."
        return text[:3000]  # limit size
    except:
        return "Resume extraction failed — using fallback text."


# -----------------------------------------
# MAIN AI ENDPOINT (NEVER CRASHES)
# -----------------------------------------
@app.post("/api/ai_full_analysis")
async def ai_full_analysis(resume: UploadFile = File(...)):
    text = await extract_text(resume)

    # Mock ATS score (replace later if needed)
    ats_score = 62  

    # Extract very primitive sample skills
    skills = []
    for s in ["python", "sql", "power bi", "tableau", "excel"]:
        if s in text.lower():
            skills.append(s)

    required = ["python", "sql", "power bi"]
    missing = [s for s in required if s not in skills]

    # Synthetic salary mock
    salary_range = {"min": 300000, "median": 450000, "max": 900000}

    # Synthetic distribution
    distribution = {
        "labels": ["0–3L", "3–6L", "6–9L", "9–12L"],
        "counts": [3, 6, 5, 2]
    }

    # Learning plan
    ai_plan = {
        "priority": ["python", "sql", "excel"],
        "roadmap": {
            "python": {
                "steps": ["Basics", "Mini projects"],
                "resources": ["https://youtu.be/...", "https://coursera.org"]
            },
            "sql": {
                "steps": ["Queries", "Joins", "Case studies"],
                "resources": ["https://mode.com/sql-tutorial"]
            }
        },
        "short_note": "Focus on missing skills and build portfolio projects."
    }

    # Return SAFE payload
    return {
        "ats": ats_score,
        "required_skills": required,
        "matched_skills": skills,
        "missing_skills": missing,
        "salary_range": salary_range,
        "salary_distribution": distribution,
        "demand_score": 75,
        "ai_plan": ai_plan,
        "jobs": [
            {"title": "Data Analyst", "company": "ABC Corp", "location": "Pune"},
            {"title": "Business Analyst", "company": "XYZ Ltd", "location": "Remote"}
        ],
        "raw_resume_sample": text[:200]
    }


# -----------------------------------------
# START BACKEND
# -----------------------------------------
print("🚀 Backend running at http://127.0.0.1:5000")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
