# server.py
# FastAPI backend for Resume -> full AI analysis
# Requires: DEEPSEEK_API_KEY, JSEARCH_API_KEY in .env OR environment

import os
import io
import json
import re
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
import docx
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY", "")

app = FastAPI(title="Resume Analysis Proxy")

# allow local dev browser to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = []
        for p in reader.pages:
            t = p.extract_text()
            if t:
                text.append(t)
        return "\n".join(text)
    except Exception:
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""

def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception:
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""

def call_deepseek_prompt(prompt: str, max_tokens=600):
    if not DEEPSEEK_API_KEY:
        return {"error": "DEEPSEEK_API_KEY missing"}
    url = "https://api.deepseek.com/v1/chat/completions"
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are an assistant that extracts skills and estimates salary/demand in INR for India market."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    try:
        return resp.json()
    except Exception:
        return {"error": "DeepSeek response parse error", "text": resp.text}

def call_jsearch(query: str):
    # JSearch RapidAPI endpoint - returns jobs (if key present)
    if not JSEARCH_API_KEY:
        return {"error": "JSEARCH_API_KEY missing"}
    url = "https://jsearch.p.rapidapi.com/search"
    params = {"query": query, "page": 1, "num_pages": 1}
    headers = {"X-RapidAPI-Key": JSEARCH_API_KEY, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"}
    resp = requests.get(url, headers=headers, params=params, timeout=20)
    try:
        return resp.json()
    except Exception:
        return {"error": "JSearch parse error", "text": resp.text}

def parse_salary_from_text(s: str):
    # attempt to find numbers in INR-like format; fallback to None
    try:
        # find all numbers > 10000 (annual rupee)
        nums = re.findall(r"[₹]?\s*([0-9]{3,}[,\d]*)", s.replace(" ", ""))
        cleaned = []
        for n in nums:
            n2 = n.replace(",", "")
            try:
                cleaned.append(int(n2))
            except:
                pass
        if cleaned:
            mn = min(cleaned); mx = max(cleaned)
            median = int((mn + mx) / 2)
            return {"min": mn, "median": median, "max": mx}
    except:
        pass
    return None

@app.post("/api/ai_full_analysis")
async def ai_full_analysis(file: UploadFile = File(...)):
    """
    Accepts resume file (pdf/docx/txt). Returns a JSON with:
      - salary_range {min,median,max}
      - demand_score (0-100)
      - required_skills (list)
      - matched_skills (list)  <-- empty here (we don't have candidate profile separate)
      - missing_skills (list)
      - ai_plan (string or JSON)
      - jobs (list)
      - salary_distribution {labels, counts}
      - resume_text (string)
    """
    data = await file.read()
    fname = (file.filename or "").lower()
    if fname.endswith(".pdf"):
        text = extract_text_from_pdf(data)
    elif fname.endswith(".docx") or fname.endswith(".doc"):
        text = extract_text_from_docx(data)
    else:
        try:
            text = data.decode("utf-8", errors="ignore")
        except:
            text = ""

    if not text or len(text) < 20:
        raise HTTPException(status_code=400, detail="Could not extract text from resume")

    # 1) Ask DeepSeek to extract top skills + a salary estimate + demand score + learning plan
    prompt = (
        "From the resume text below, extract:\n"
        "1) a short list of top technical/role skills (comma separated),\n"
        "2) estimate a realistic annual salary range (min, median, max) in Indian rupees (INR) for this candidate in India,\n"
        "3) give an estimated demand score 0-100 for hiring this role in India,\n"
        "4) produce a JSON learning plan with: missing (skills), priority (top 3), roadmap { skill: { steps:[], resources:[] } }, short_note.\n\n"
        "Output MUST include a JSON block for the learning plan and include the salary numbers in plain text too.\n\n"
        f"Resume:\n\n{text[:4500]}\n\n"
    )
    ds_resp = call_deepseek_prompt(prompt)
    # DeepSeek response parsing
    # try to find text content
    ai_text = ""
    if isinstance(ds_resp, dict):
        # typical DeepSeek: { choices: [ { message: { content: "..." } } ] }
        try:
            ai_text = ds_resp.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            ai_text = ds_resp.get("text") or ""
    else:
        ai_text = str(ds_resp)

    # parse skills (simple heuristics)
    skills = []
    # try to parse JSON from ai_text for plan and maybe skills
    plan_json = None
    try:
        # find JSON object inside response
        start = ai_text.find("{")
        end = ai_text.rfind("}")
        if start >= 0 and end > start:
            maybe = ai_text[start:end+1]
            plan_json = json.loads(maybe)
    except Exception:
        plan_json = None

    # get skills by regex fallback
    skills_found = re.findall(r"(?:Skills|Top skills|Top Skills|Top Skills:)\s*[:\-]?\s*(.+)", ai_text, flags=re.IGNORECASE)
    if skills_found:
        # take first and split
        skills = [s.strip().lower() for s in re.split(r"[,\n;|/]+", skills_found[0]) if s.strip()]
    else:
        # fallback generic extraction of common skills
        fallback = re.findall(r"(Python|SQL|Excel|Power BI|Tableau|AWS|Docker|Kubernetes|Pandas|NumPy|R|Java|Spark|Hadoop|Machine Learning|Deep Learning|Tableau|PowerBI)", text, flags=re.I)
        skills = [s.strip().lower() for s in set(fallback)]

    # parse salary numbers from ai_text
    salary = parse_salary_from_text(ai_text) or parse_salary_from_text(text)

    # attempt to get demand score from ai_text
    demand_score = None
    try:
        m = re.search(r"(\d{1,3})\s*\/\s*100", ai_text)
        if m:
            demand_score = int(m.group(1))
    except:
        demand_score = None

    if demand_score is None:
        # fallback estimate
        demand_score = 60 if skills else 40

    # 2) Try to fetch job postings from JSearch (best-effort)
    jobs = []
    try:
        # compose a role query: top skill or first noun phrase
        q = skills[0] if skills else ""
        jresp = call_jsearch(q + " india")
        # jresp typically has jresp.get("data", [])
        if isinstance(jresp, dict) and "data" in jresp:
            for j in jresp["data"][:8]:
                jobs.append({
                    "title": j.get("job_title") or j.get("title") or "",
                    "company": j.get("employer_name") or j.get("company_name") or "",
                    "location": j.get("job_city") or j.get("job_country") or j.get("location") or "",
                    "description": j.get("job_description") or ""
                })
    except Exception:
        jobs = []

    # build salary distribution synthetic (around median)
    if salary:
        mn = salary["min"]
        md = salary["median"]
        mx = salary["max"]
        # create 4 buckets between min and max
        buckets = []
        counts = []
        try:
            rng = (mx - mn) // 4 or 1
            for i in range(4):
                a = mn + i * rng
                b = a + rng
                buckets.append(f"₹{a//100000}-{b//100000}L")
                counts.append(max(1, 6 - i))  # simple synthetic counts
        except:
            buckets = ["0-3L","3-6L","6-9L","9-12L"]
            counts = [2,6,10,5]
    else:
        mn, md, mx = (300000, 600000, 1200000)
        buckets = ["3-5L","5-7L","7-9L","9-12L"]
        counts = [2,6,5,1]

    # ai_plan: prefer plan_json else create small plan using text
    ai_plan = plan_json if plan_json else {
        "priority": skills[:3],
        "roadmap": { s: {"steps": ["Learn basics", "Build small project", "Include in resume"], "resources": ["https://youtube.com","https://coursera.org"]} for s in skills[:4]},
        "short_note": "Focus on top missing skills and build small projects to demonstrate them."
    }

    required_skills = skills
    matched_skills = []  # we only analyzed resume (so matched==extracted)
    missing_skills = []  # nothing to compare to (could be role top-skills vs candidate), so keep empty

    payload = {
        "resume_text": text[:6000],
        "salary_range": {"min": mn, "median": md, "max": mx},
        "demand_score": demand_score,
        "required_skills": required_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "ai_plan": ai_plan,
        "jobs": jobs,
        "salary_distribution": {"labels": buckets, "counts": counts},
        "ai_raw": ai_text
    }

    return payload

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Backend on http://127.0.0.1:5000 ...")
    uvicorn.run(app, host="127.0.0.1", port=5000)
