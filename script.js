// assets/script.js

const API = "http://127.0.0.1:5000/api/full_analysis";

const resumeFile = document.getElementById("resumeFile");
const jdFile = document.getElementById("jdFile");
const analyzeBtn = document.getElementById("analyzeBtn");

const atsScoreEl = document.getElementById("atsScore");
const topSkillsEl = document.getElementById("topSkills");
const missingSkillsEl = document.getElementById("missingSkills");
const aiPlanEl = document.getElementById("aiPlan");
const rawOutput = document.getElementById("rawOutput");

let salaryChart, matchChart;

// POST resume + JD → backend
async function analyze() {
    if (!resumeFile.files[0] || !jdFile.files[0]) {
        alert("Please upload BOTH Resume & JD");
        return;
    }

    const fd = new FormData();
    fd.append("resume", resumeFile.files[0]);
    fd.append("jd", jdFile.files[0]);

    try {
        const resp = await fetch(API, {
            method: "POST",
            body: fd
        });

        const data = await resp.json();
        render(data);

    } catch (err) {
        alert("Error: " + err);
    }
}

function render(data) {
    rawOutput.textContent = JSON.stringify(data, null, 2);

    // ATS Score
    atsScoreEl.textContent = data.ats.ats_score + "%";

    // Skills
    topSkillsEl.textContent = data.ats.matched_skills.join(", ") || "—";
    missingSkillsEl.textContent = data.ats.missing_skills.join(", ") || "—";

    // Salary Chart
    makeSalaryChart(
        data.salary_distribution.labels,
        data.salary_distribution.counts
    );

    // Skill Match Chart
    makeMatchChart(
        data.ats.matched_skills.length,
        data.ats.missing_skills.length
    );

    // AI Plan
    aiPlanEl.innerHTML = `
        <strong>Priority:</strong> ${data.ai_plan.priority.join(", ")}<br>
        <strong>Learning:</strong><br>
        Python → ${data.ai_plan.roadmap.python.steps.join(", ")}<br>
        SQL → ${data.ai_plan.roadmap.sql.steps.join(", ")}
    `;
}

function makeSalaryChart(labels, counts) {
    const ctx = document.getElementById("salaryChart");

    if (salaryChart) salaryChart.destroy();

    salaryChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Count",
                data: counts,
                backgroundColor: "#62b4ff"
            }]
        }
    });
}

function makeMatchChart(matched, missing) {
    const ctx = document.getElementById("matchChart");

    if (matchChart) matchChart.destroy();

    matchChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Matched", "Missing"],
            datasets: [{
                data: [matched, missing],
                backgroundColor: ["#4caf50", "#ff5252"]
            }]
        }
    });
}

analyzeBtn.onclick = analyze;
