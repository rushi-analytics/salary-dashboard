const API_BASE = "http://127.0.0.1:5000";

const resumeFile = document.getElementById('resumeFile');
const analyzeBtn = document.getElementById('analyzeBtn');
const spinner = document.getElementById('spinner');

// UI elements
const atsScoreEl = document.getElementById('atsScore');
const statSalary = document.getElementById('statSalary');
const statDemand = document.getElementById('statDemand');
const topSkillsEl = document.getElementById('topSkills');
const missingSkillsEl = document.getElementById('missingSkills');
const jobListEl = document.getElementById('jobList');
const aiPlanEl = document.getElementById('aiPlan');
const rawOutput = document.getElementById('rawOutput');

// charts
let salaryChart = null;
let skillChart = null;

// spinner
function showSpinner(on) {
    spinner.style.display = on ? "inline-block" : "none";
}

// send resume to backend
async function postResumeAndAnalyze(file) {
    if (!file) return alert("Please upload a resume.");

    showSpinner(true);
    const fd = new FormData();
    fd.append("file", file, file.name);

    try {
        const resp = await fetch(`${API_BASE}/api/ai_full_analysis`, {
            method: "POST",
            body: fd
        });

        if (!resp.ok) throw new Error("Server error");

        const data = await resp.json();
        renderAll(data);

    } catch (err) {
        alert("Analysis failed: " + err.message);
    }

    showSpinner(false);
}

// render data
function renderAll(data) {
    rawOutput.textContent = JSON.stringify(data, null, 2);

    // A — ATS Score
    atsScoreEl.textContent = data.ats + "%";

    // Salary + Demand
    statSalary.textContent = 
        `Salary — Min: ₹${data.salary_range.min} Median: ₹${data.salary_range.median} Max: ₹${data.salary_range.max}`;
    statDemand.textContent = `Demand: ${data.demand_score}/100`;

    // B — Skills
    topSkillsEl.textContent = data.matched_skills.join(", ") || "—";
    missingSkillsEl.textContent = data.missing_skills.join(", ") || "—";

    // C — Salary Chart
    makeSalaryChart(data.salary_distribution.labels, data.salary_distribution.counts);

    // C — Skill Match Chart
    makeSkillChart(
        data.required_skills.length,
        data.matched_skills.length
    );

    // D — Jobs
    jobListEl.innerHTML = data.jobs.map(j =>
        `<div><strong>${j.title}</strong> — ${j.company} (${j.location})</div>`
    ).join("");

    // D — AI Learning Plan
    let html = `<strong>Priority:</strong> ${data.ai_plan.priority.join(", ")}<br><br>`;
    for (const [skill, plan] of Object.entries(data.ai_plan.roadmap)) {
        html += `<strong>${skill}</strong><br>
                 Steps: ${plan.steps.join(" | ")}<br>
                 Resources: ${plan.resources.join(" | ")}<br><br>`;
    }
    aiPlanEl.innerHTML = html;
}

// Chart functions
function makeSalaryChart(labels, counts) {
    const ctx = document.getElementById("chartSalaryDist").getContext("2d");
    if (salaryChart) salaryChart.destroy();
    salaryChart = new Chart(ctx, {
        type: "bar",
        data: { labels, datasets: [{ data: counts }] },
        options: { scales: { y: { beginAtZero: true } } }
    });
}

function makeSkillChart(required, matched) {
    const ctx = document.getElementById("chartSkillMatch").getContext("2d");
    if (skillChart) skillChart.destroy();
    skillChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Matched", "Missing"],
            datasets: [{ data: [matched, required - matched] }]
        },
        options: { plugins: { legend: { position: "bottom" } } }
    });
}

// button handler
analyzeBtn.addEventListener("click", () => {
    const file = resumeFile.files[0];
    postResumeAndAnalyze(file);
});
