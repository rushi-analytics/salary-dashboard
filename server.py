# server.py
import os, io, json, random, traceback
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PyPDF2 import PdfReader
import docx
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY", "")

app = FastAPI(title="Salary Dashboard AI Proxy")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ---------------- helpers extract ----------------
def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text.append(t)
        return "\n".join(text)
    except Exception:
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except:
            return ""

def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception:
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except:
            return ""

# ----------------- fallback analyzer -----------------
COMMON_SKILLS = ["python","sql","excel","power bi","tableau","aws","docker","kubernetes",
                 "r","pandas","numpy","scikit-learn","spark","hadoop","ml","deep learning",
                 "git","aws","azure","gcp","javascript","html","css"]

def fallback_analyze(text: str) -> dict:
    # simple skill extraction (regex-like)
    found = set()
    t = (text or "").lower()
    for s in COMMON_SKILLS:
        if s in t:
            found.add(s)
    extracted = sorted(list(found))
    required_skills = extracted[:6] if extracted else ["python","sql","excel"]
    matched = extracted
    missing = [s for s in required_skills if s not in matched]
    # synthetic salary stats and distribution
    base = random.randint(400000,900000)
    salary_range = {"min": base, "median": base + 150000, "max": base + 600000}
    # create 5 buckets labels/counts
    labels = ["0-3L","3-6L","6-9L","9-12L","12L+"]
    counts = [random.randint(1,6) for _ in labels]
    # demand synthetic
    demand_score = random.randint(30,85)
    # simple fit score
    skill_match_pct = int((len(matched) / max(1, len(required_skills))) * 100)
    resume_fit_score = int(skill_match_pct * 0.7 + (demand_score * 0.2) + 10)  # small weighting
    # ai plan skeleton
    plan = {
        "priority": required_skills[:3],
        "roadmap": { s: {"steps":[f"Learn basics of {s}","Build a small project","Add to resume"], "resources":["https://example.com","https://youtube.com"]} for s in required_skills[:3] },
        "short_note": "Focus on the top 3 skills above and demonstrate them with projects."
    }
    return {
        "text": (text or "")[:4000],
        "extracted_skills": extracted,
        "required_skills": required_skills,
        "matched_skills": matched,
        "missing_skills": missing,
        "salary_range": salary_range,
        "salary_distribution": {"labels": labels, "counts": counts},
        "demand_score": demand_score,
        "resume_fit_score": max(0, min(100, resume_fit_score)),
        "ai_plan": plan,
        "jobs": []  # empty fallback
    }

# --------------- external calls (optional) ----------------
def call_deepseek_for_skills(text: str) -> str:
    if not DEEPSEEK_API_KEY:
        return None
    url = "https://api.deepseek.com/v1/chat/completions"
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role":"system", "content":"Extract top skills and recommend missing skills in JSON. Output only JSON."},
            {"role":"user", "content": f"Resume text:\n\n{text}\n\nReturn JSON: {json.dumps({'fields':['skills','recommended','notes']})}"}
        ],
        "max_tokens": 400
    }
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type":"application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    j = resp.json()
    # Try to extract text content
    try:
        content = j.get("choices",[{}])[0].get("message",{}).get("content","")
        return content
    except Exception:
        return None

def call_jsearch(role: str):
    if not JSEARCH_API_KEY:
        return None
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {"X-RapidAPI-Key": JSEARCH_API_KEY, "X-RapidAPI-Host":"jsearch.p.rapidapi.com"}
    params = {"query": role, "page":1, "num_pages":1}
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()

# ---------------- endpoint: extract + full analysis ----------------
@app.post("/api/ai_full_analysis")
async def ai_full_analysis(file: UploadFile = File(...)):
    try:
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
        # try external AI if configured
        result = None
        try:
            if DEEPSEEK_API_KEY:
                ai_text = call_deepseek_for_skills(text)
                if ai_text:
                    # try parse JSON inside ai_text
                    j = None
                    try:
                        # extract JSON substring if present
                        start = ai_text.find('{')
                        if start != -1:
                            j = json.loads(ai_text[start:])
                    except Exception:
                        j = None
                    if j:
                        # build structured response from j
                        skills = j.get('skills') or j.get('top_skills') or []
                        recommended = j.get('recommended') or j.get('recommended_skills') or []
                        plan = j.get('plan') or {"priority": recommended[:3], "roadmap": {}, "short_note": j.get('notes','')}
                        # synthetic salary/demand via heuristics (we still need numbers)
                        salary_range = {"min":500000,"median":800000,"max":1500000}
                        distro = {"labels":["0-3L","3-6L","6-9L","9-12L","12L+"],"counts":[2,6,12,4,1]}
                        jobs = []
                        matched = [s for s in skills if s in text.lower()]  # crude
                        missing = [s for s in skills if s not in matched]
                        resume_fit_score = int((len(matched)/max(1,len(skills))) * 100 * 0.7 + 15)
                        result = {
                            "text": text[:4000],
                            "extracted_skills": skills,
                            "required_skills": skills,
                            "matched_skills": matched,
                            "missing_skills": missing,
                            "salary_range": salary_range,
                            "salary_distribution": distro,
                            "demand_score": 70,
                            "resume_fit_score": resume_fit_score,
                            "ai_plan": plan,
                            "jobs": jobs,
                            "components": {"skillComponent": int((len(matched)/max(1,len(skills)))*70), "demandComponent":int(70*0.2), "salaryComponent":int(10)}
                        }
            # else fallback
        except Exception as e:
            # log but continue to fallback
            print("DeepSeek call failed:", e)
            result = None

        if not result:
            # fallback analyzer
            result = fallback_analyze(text)

        # try to enrich with JSearch if configured and role present
        role_guess = None
        if result.get("required_skills"):
            # naive role guess: first skill + 'engineer' or 'analyst'
            role_guess = (result["required_skills"][0] + " analyst") if result["required_skills"] else ""
        if JSEARCH_API_KEY and role_guess:
            try:
                j = call_jsearch(role_guess)
                # map a little
                jobs = []
                for it in (j.get("data") or [])[:10]:
                    jobs.append({
                        "title": it.get("job_title") or it.get("title"),
                        "company": it.get("employer_name") or it.get("company_name"),
                        "location": it.get("job_city") or it.get("job_country"),
                        "description": it.get("job_description")
                    })
                result["jobs"] = jobs
                result["demand_score"] = int(result.get("demand_score",50) + min(30, len(jobs)))  # bump slightly
            except Exception as e:
                print("JSearch call failed:", e)

        # components: ensure present
        if "components" not in result:
            result["components"] = {
                "skillComponent": int((len(result.get("matched_skills",[])) / max(1, len(result.get("required_skills",[]))))*70) if result.get("required_skills") else 0,
                "demandComponent": int((result.get("demand_score",0)/100)*20),
                "salaryComponent": int( ( (result.get("salary_range",{}).get("median",0) / max(1,result.get("salary_range",{}).get("max",1))) * 10 ) )
            }

        return JSONResponse(result)
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"error":"internal server error", "detail": str(e)}, status_code=500)

# small root health check
@app.get("/api/ping")
def ping():
    return {"status":"ok"}
