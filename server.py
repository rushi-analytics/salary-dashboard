from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import requests
import base64

app = FastAPI()

# Allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# 🔹 Resume Extract Endpoint
# ======================
@app.post("/api/extract")
async def extract_resume(file: UploadFile = File(...)):
    try:
        content = await file.read()
        text = content.decode("utf-8", errors="ignore")
        return {"text": text}
    except Exception as e:
        return {"error": str(e)}

# ======================
# 🔹 Analyze Text (Skills, Summary, Score)
# ======================
@app.post("/api/analyze")
async def analyze_resume(text: str = Form(...)):
    # Simple local scoring logic
    words = text.split()
    score = min(100, len(words) // 10)

    return {
        "fit_score": score,
        "recommendations": [
            "Add measurable project outcomes.",
            "Include top in-demand skills.",
            "Use action verbs to improve impact."
        ],
        "missing_skills": ["Python", "SQL", "Power BI"][:3]
    }

# ======================
# Server Start
# ======================
if __name__ == "__main__":
    print("🚀 Starting Backend on http://127.0.0.1:5000 ...")
    uvicorn.run(app, host="127.0.0.1", port=5000)
