/* ======================
   BACKEND CONFIG
   ====================== */
const API_BASE = "http://127.0.0.1:5000";

/* ======================
   UTILITIES
   ====================== */
function toNumber(v) {
  return v === "" || v === null || v === undefined ? NaN : +v;
}

function medianCalc(arr) {
  const s = arr.slice().sort((a, b) => a - b);
  const n = s.length;
  if (n === 0) return NaN;
  const m = Math.floor(n / 2);
  return n % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function parseSkills(text) {
  if (!text) return [];
  return text
    .toString()
    .split(/[;,|\/]+/)
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
}

function uniq(arr) {
  return Array.from(new Set(arr));
}

function safeVal(r, keys) {
  for (const k of keys)
    if (r[k] !== undefined && r[k] !== null) return r[k];
  return "";
}

/* ======================
   GLOBAL STATE
   ====================== */
let rawData = [];
let filtered = [];

/* ======================
   DOM ELEMENTS
   ====================== */
const fileInput = document.getElementById("fileInput");
const roleFilter = document.getElementById("roleFilter");
const countryFilter = document.getElementById("countryFilter");
const expFilter = document.getElementById("expFilter");
const userSkillsInput = document.getElementById("userSkills");
const analyzeBtn = document.getElementById("analyzeBtn");
const downloadBtn = document.getElementById("downloadBtn");
const resumeFile = document.getElementById("resumeFile");
const aiRecEl = document.getElementById("aiRecommendations");
const avgEl = document.getElementById("avg");
const medianEl = document.getElementById("median");
const minEl = document.getElementById("min");
const maxEl = document.getElementById("max");
const insightsContainer = document.getElementById("insightsContainer");

/* ======================
   CHARTS
   ====================== */
let salaryDistChart, salaryByExpChart, cityBarChart;

function createChart(ctx, cfg) {
  return new Chart(ctx, cfg);
}

function buildCharts() {
  salaryDistChart = createChart(document.getElementById("salaryDist"), {
    type: "bar",
    data: { labels: [], datasets: [{ label: "Count", data: [], backgroundColor: "rgba(47,156,240,0.6)" }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
  });

  salaryByExpChart = createChart(document.getElementById("salaryByExp"), {
    type: "bar",
    data: { labels: [], datasets: [{ label: "Avg Salary", data: [], backgroundColor: "rgba(47,156,240,0.6)" }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
  });

  cityBarChart = createChart(document.getElementById("cityBar"), {
    type: "bar",
    data: { labels: [], datasets: [{ label: "Avg Salary", data: [], backgroundColor: "rgba(47,156,240,0.6)" }] },
    options: { indexAxis: "y", responsive: true, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true } } },
  });
}

buildCharts();

/* ======================
   CSV Loader
   ====================== */
function mapRow(r) {
  return {
    role: safeVal(r, ["role", "Role", "job", "Job"]).trim(),
    country: safeVal(r, ["country", "Country"]).trim(),
    city: safeVal(r, ["city", "City"]).trim(),
    experience_years: safeVal(r, ["experience_years", "experience", "Experience"]).trim(),
    annual_salary_inr: safeVal(r, ["annual_salary_inr", "annual_salary", "salary", "Salary"])
      .toString()
      .replace(/,/g, "")
      .trim(),
    top_skills: safeVal(r, ["top_skills", "skills", "Skills"]).trim(),
    demand_score: safeVal(r, ["demand_score"]).trim(),
    postings: safeVal(r, ["postings"]).trim(),
  };
}

fileInput.addEventListener("change", (e) => {
  const f = e.target.files[0];
  if (!f) return;

  Papa.parse(f, {
    header: true,
    skipEmptyLines: true,
    complete(results) {
      rawData = results.data.map(mapRow);
      updateFiltersUI();
      applyFilters();
    },
  });
});

/* Load sample CSV */
fetch("data/sample_salaries.csv")
  .then((r) => r.text())
  .then((txt) => {
    Papa.parse(txt, {
      header: true,
      skipEmptyLines: true,
      complete(res) {
        rawData = res.data.map(mapRow);
        updateFiltersUI();
        applyFilters();
      },
    });
  });

/* ======================
   FILTER UI
   ====================== */
function updateFiltersUI() {
  const roles = uniq(rawData.map((r) => r.role)).filter(Boolean).sort();
  const countries = uniq(rawData.map((r) => r.country)).filter(Boolean).sort();

  roleFilter.innerHTML = `<option value="">All Roles</option>${roles.map((x) => `<option>${x}</option>`).join("")}`;
  countryFilter.innerHTML = `<option value="">All Countries</option>${countries.map((x) => `<option>${x}</option>`).join("")}`;
}

[roleFilter, countryFilter, expFilter].forEach((el) => el.addEventListener("change", applyFilters));

/* ======================
   FILTER EXECUTION
   ====================== */
function applyFilters() {
  const role = roleFilter.value;
  const country = countryFilter.value;
  const exp = expFilter.value;

  filtered = rawData.filter((r) => {
    if (role && r.role !== role) return false;
    if (country && r.country !== country) return false;

    const yrs = toNumber(r.experience_years);
    if (!isNaN(yrs) && exp) {
      if (exp === "0-1" && !(yrs >= 0 && yrs <= 1)) return false;
      if (exp === "1-3" && !(yrs > 1 && yrs <= 3)) return false;
      if (exp === "3-5" && !(yrs > 3 && yrs <= 5)) return false;
      if (exp === "5+" && !(yrs > 5)) return false;
    }
    return true;
  });

  renderStats();
  renderCharts();
}

/* ======================
   STATS DISPLAY
   ====================== */
function renderStats() {
  const salaries = filtered.map((r) => toNumber(r.annual_salary_inr)).filter((v) => !isNaN(v));

  if (salaries.length === 0) {
    avgEl.textContent = "Avg: -";
    medianEl.textContent = "Median: -";
    minEl.textContent = "Min: -";
    maxEl.textContent = "Max: -";
    return;
  }

  const avg = Math.round(salaries.reduce((a, b) => a + b, 0) / salaries.length);
  const med = Math.round(medianCalc(salaries));
  const min = Math.min(...salaries);
  const max = Math.max(...salaries);

  avgEl.textContent = `Avg: ₹${avg.toLocaleString()}`;
  medianEl.textContent = `Median: ₹${med.toLocaleString()}`;
  minEl.textContent = `Min: ₹${min.toLocaleString()}`;
  maxEl.textContent = `Max: ₹${max.toLocaleString()}`;
}

/* ======================
   CHARTS UPDATE
   ====================== */
function renderCharts() {
  const salaries = filtered.map((r) => toNumber(r.annual_salary_inr)).filter((v) => !isNaN(v));

  /* Salary Distribution */
  let labels = [],
    counts = [];
  if (salaries.length) {
    const buckets = 6;
    const min = Math.min(...salaries);
    const max = Math.max(...salaries);
    const range = max - min || 1;
    const size = range / buckets;

    counts = Array(buckets).fill(0);

    for (let i = 0; i < buckets; i++) {
      const a = Math.round(min + i * size);
      const b = Math.round(min + (i + 1) * size);
      labels.push(`₹${a.toLocaleString()} - ₹${b.toLocaleString()}`);
    }

    salaries.forEach((v) => {
      let idx = Math.floor((v - min) / size);
      if (idx >= buckets) idx = buckets - 1;
      counts[idx]++;
    });
  }

  salaryDistChart.data.labels = labels;
  salaryDistChart.data.datasets[0].data = counts;
  salaryDistChart.update();

  /* Salary by Experience */
  const groups = {};
  filtered.forEach((r) => {
    const yrs = toNumber(r.experience_years);
    const sal = toNumber(r.annual_salary_inr);
    if (isNaN(yrs) || isNaN(sal)) return;

    let bucket = "Unknown";
    if (yrs <= 1) bucket = "0-1";
    else if (yrs <= 3) bucket = "1-3";
    else if (yrs <= 5) bucket = "3-5";
    else bucket = "5+";

    if (!groups[bucket]) groups[bucket] = [];
    groups[bucket].push(sal);
  });

  const expLabels = Object.keys(groups).sort();
  const expData = expLabels.map((k) =>
    Math.round(groups[k].reduce((a, b) => a + b, 0) / groups[k].length)
  );

  salaryByExpChart.data.labels = expLabels;
  salaryByExpChart.data.datasets[0].data = expData;
  salaryByExpChart.update();

  /* Top Cities */
  const cityMap = {};
  filtered.forEach((r) => {
    const c = r.city || "Unknown";
    const sal = toNumber(r.annual_salary_inr);
    if (isNaN(sal)) return;

    if (!cityMap[c]) cityMap[c] = [];
    cityMap[c].push(sal);
  });

  const cityArr = Object.entries(cityMap)
    .map(([c, arr]) => ({ city: c, avg: arr.reduce((a, b) => a + b, 0) / arr.length }))
    .sort((a, b) => b.avg - a.avg)
    .slice(0, 8);

  cityBarChart.data.labels = cityArr.map((x) => x.city);
  cityBarChart.data.datasets[0].data = cityArr.map((x) => Math.round(x.avg));
  cityBarChart.update();
}

/* ======================
   BACKEND CALLS
   ====================== */
async function extractResumeTextBackend(file) {
  const fd = new FormData();
  fd.append("file", file, file.name);

  const res = await fetch(`${API_BASE}/api/extract_resume`, {
    method: "POST",
    body: fd,
  });

  return res.ok ? await res.json() : { text: "" };
}

async function getAISkillsBackend(text) {
  const fd = new FormData();
  fd.append("text", text);

  const res = await fetch(`${API_BASE}/api/ai_skills`, {
    method: "POST",
    body: fd,
  });

  return res.ok ? await res.json() : { skills: "" };
}

async function getAIPlanBackend(role, top_skills, user_skills) {
  const fd = new FormData();
  fd.append("role", role);
  fd.append("top_skills", top_skills);
  fd.append("user_skills", user_skills);

  const res = await fetch(`${API_BASE}/api/ai_plan`, {
    method: "POST",
    body: fd,
  });

  return res.ok ? await res.json() : { plan: "" };
}

async function fetchJobDemandFromAPI(query) {
  try {
    const res = await fetch(`${API_BASE}/api/job_demand?role=${encodeURIComponent(query)}`);
    return res.ok ? await res.json() : null;
  } catch (e) {
    return null;
  }
}

/* ======================
   INSIGHT + FIT CALC
   ====================== */
function computeInsights() {
  const rows = filtered.slice();
  const salaries = rows.map((r) => toNumber(r.annual_salary_inr)).filter((v) => !isNaN(v));

  const skillCounts = {};
  rows.forEach((r) => {
    parseSkills(r.top_skills).forEach((s) => {
      skillCounts[s] = (skillCounts[s] || 0) + 1;
    });
  });

  return {
    rows,
    salaries,
    minV: salaries.length ? Math.min(...salaries) : null,
    medV: salaries.length ? Math.round(medianCalc(salaries)) : null,
    maxV: salaries.length ? Math.max(...salaries) : null,
    avgV: salaries.length
      ? Math.round(salaries.reduce((a, b) => a + b, 0) / salaries.length)
      : null,
    postings: rows.reduce((s, r) => s + (Number(r.postings) || 0), 0),
    avgDemandScore: rows.length
      ? Math.round(
          rows.reduce((s, r) => s + (Number(r.demand_score) || 0), 0) / rows.length
        )
      : 0,
    topSkills: Object.entries(skillCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map((x) => x[0]),
    globalMin: Math.min(...rawData.map((r) => toNumber(r.annual_salary_inr)).filter((v) => !isNaN(v))),
    globalMax: Math.max(...rawData.map((r) => toNumber(r.annual_salary_inr)).filter((v) => !isNaN(v))),
  };
}

function computeResumeFit(ins, userSkills) {
  const req = ins.topSkills;
  const user = parseSkills(userSkills);

  const matched = req.filter((s) => user.includes(s));
  const missing = req.filter((s) => !user.includes(s));

  const score = Math.round((matched.length / req.length) * 100);

  return { score, matched, missing };
}

/* ======================
   MAIN ANALYZE LOGIC
   ====================== */
async function renderInsights() {
  insightsContainer.innerHTML = "";

  const insights = computeInsights();
  const userSkills = userSkillsInput.value.trim();

  const roleForAI = insights.rows[0]?.role || "";

  const jd = await fetchJobDemandFromAPI(roleForAI);

  const fit = computeResumeFit(insights, userSkills);

  /* Salary Card */
  insightsContainer.innerHTML += `
    <div class="insight-card">
      <h3>Salary Range</h3>
      <div>Min: ₹${insights.minV || "-"} | Median: ₹${insights.medV || "-"} | Max: ₹${insights.maxV || "-"}</div>
      <div>Avg: ₹${insights.avgV || "-"}</div>
    </div>`;

  /* Demand */
  insightsContainer.innerHTML += `
    <div class="insight-card">
      <h3>Market Demand</h3>
      <div>Postings: ${jd?.count || insights.postings}</div>
      <div>Demand Score: ${(jd?.avgScore || insights.avgDemandScore)}/100</div>
    </div>`;

  /* Skills */
  insightsContainer.innerHTML += `
    <div class="insight-card">
      <h3>Skill Gap</h3>
      <div>Top Skills: ${insights.topSkills.join(", ")}</div>
    </div>`;

  /* Fit Score */
  insightsContainer.innerHTML += `
    <div class="insight-card">
      <h3>Resume Fit</h3>
      <div class="fit-score">${fit.score}%</div>
      <div>Missing: ${fit.missing.map((x) => `<span class="chip">${x}</span>`).join("")}</div>
    </div>`;
}

/* ======================
   EVENTS
   ====================== */
analyzeBtn.addEventListener("click", async () => {
  applyFilters();
  await renderInsights();
});

downloadBtn.addEventListener("click", () => {
  const rows = filtered.map((r) => ({
    role: r.role,
    country: r.country,
    city: r.city,
    experience: r.experience_years,
    salary: r.annual_salary_inr,
    skills: r.top_skills,
    demand_score: r.demand_score,
    postings: r.postings,
  }));

  const csv = Papa.unparse(rows);
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = "filtered_salaries.csv";
  a.click();
});
