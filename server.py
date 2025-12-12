from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

# Enable CORS for frontend (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# Utility functions
# -------------------------------
def extract_text(file_bytes: bytes):
    return file_bytes.decode("utf-8", errors="ignore")

def find_skills(text):
    keywords = ["python","sql","excel","tableau","power bi","aws","azure","gcp",
                "docker","pandas","numpy","machine learning","data analysis"]
    text = text.lower()
    return [s for s in keywords if s in text]

# -------------------------------
# MAIN API ROUTE
# -------------------------------
@app.post("/api/ai_full_analysis")
async def analyze(file: UploadFile = File(...)):

    resume_bytes = await file.read()
    text = extract_text(resume_bytes)
    extracted = find_skills(text)

    required = ["python","sql","excel","power bi","tableau"]
    matched = [s for s in required if s in extracted]
    missing = [s for s in required if s not in extracted]

    score = int((len(matched) / len(required)) * 100)

    data = {
        "salary_range": {"min": 300000, "median": 650000, "max": 1200000},
        "demand_score": 75,
        "resume_fit_score": score,
        "components": {
            "skillComponent": score,
            "demandComponent": 15,
            "salaryComponent": 10
        },
        "required_skills": required,
        "matched_skills": matched,
        "missing_skills": missing,
        "salary_distribution": {
            "labels": ["3-5L","5-7L","7-9L","9-12L"],
            "counts": [3, 6, 5, 2]
        },
        "ai_plan": {
            "priority": missing[:3],
            "roadmap": {m: {"steps": ["Learn basics", "Build projects"], 
                            "resources": ["https://youtube.com", "https://coursera.org"]} 
                        for m in missing},
            "short_note": "Upskill to improve match score."
        },
        "jobs": [
            {"title": "Data Analyst", "company": "ABC Corp", "location": "Pune"},
            {"title": "Business Analyst", "company": "XYZ Ltd", "location": "Remote"}
        ],
        "raw_text": text[:500]
    }

    return data

# -------------------------------
# START SERVER
# -------------------------------
if __name__ == "__main__":
    print("🚀 Starting backend at http://127.0.0.1:5000")
    uvicorn.run(app, host="127.0.0.1", port=5000)
