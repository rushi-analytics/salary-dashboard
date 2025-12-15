// ===============================
// Backend API URL
// ===============================
const API_BASE = "http://127.0.0.1:5000";

// ===============================
// DOM ELEMENTS
// ===============================
const resumeFile = document.getElementById("resumeFile");
const analyzeBtn = document.getElementById("analyzeBtn");
const spinner = document.getElementById("spinner");

const atsScoreEl = document.getElementById("atsScore");
const statSalary = document.getElementById("statSalary");
const statDemand = document.getElementById("statDemand");
const topSkillsEl = document.getElementById("topSkills");
const missingSkillsEl = document.getElementById("missingSkills");
const jobListEl = document.getElementById("jobList");
const aiPlanEl = document.getElementById("aiPlan");
const rawOutput = document.getElementById("rawOutput");

let salaryChart = null;
let skillChart = null;

// ===============================
// UI HELPERS
// ===============================
function showSpinner(on) {
  spinner.style.display = on ? "inline-block" : "none";
}

// ===============================
// FILE UPLOAD + ANALYZE
// ===============================
async function postResumeAndAnalyze(file) {
  if (!file) {
    alert("Please select a resume file");
    return;
  }

  showSpinner(true);

  const fd = new FormData();
  fd.append("resume", file);

  try {
    const resp = await fetch(`${API_BASE}/api/ai_full_analysis`, {
      method: "POST",
      body: fd
    });

    const data = await resp.json();
    renderAll(data);

  } catch (err) {
    console.error(err);
    alert("Analysis failed");
  } finally {
    showSpinner(false);
  }
}

// ===============================
// RENDER ALL DATA (SAFE)
// ===============================
function renderAll(data) {

  if (data.error) {
    alert("AI Error. See Raw JSON.");
    rawOutput.textContent = JSON.stringify(data, null, 2);
    return;
  }

  const salary = data.salary_range || {};
  const dist = data.salary_distribution || { labels: [], counts: [] };
  const matched = data.matched_skills || [];
  const missing = data.missing_skills || [];
  const jobs = data.jobs || [];

  atsScoreEl.textContent = `${data.ats}%`;

  statSalary.textContent =
    `Salary — Min: ${salary.min} Median: ${salary.median} Max: ${salary.max}`;

  statDemand.textContent = `Demand: ${data.demand_score}`;

  topSkillsEl.textContent = matched.length ? matched.join(", ") : "—";
  missingSkillsEl.textContent = missing.length ? missing.join(", ") : "—";

  // Salary chart
  const ctx1 = document.getElementById("chartSalaryDist").getContext("2d");
  if (salaryChart) salaryChart.destroy();
  salaryChart = new Chart(ctx1, {
    type: "bar",
    data: {
      labels: dist.labels,
      datasets: [{ data: dist.counts }]
    }
  });

  // Skill chart
  const ctx2 = document.getElementById("chartSkillMatch").getContext("2d");
  if (skillChart) skillChart.destroy();
  skillChart = new Chart(ctx2, {
    type: "doughnut",
    data: {
      labels: ["Matched", "Missing"],
      datasets: [{ data: [matched.length, missing.length] }]
    }
  });

  jobListEl.innerHTML =
    jobs.length
      ? jobs.map(j => `<div>${j.title} — ${j.company} (${j.location})</div>`).join("")
      : "—";

  aiPlanEl.textContent = JSON.stringify(data.ai_plan, null, 2);
  rawOutput.textContent = JSON.stringify(data, null, 2);
}

// ===============================
// BUTTON CLICK
// ===============================
analyzeBtn.addEventListener("click", () => {
  postResumeAndAnalyze(resumeFile.files[0]);
});
