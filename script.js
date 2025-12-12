// config: backend address
const API_BASE = "http://127.0.0.1:5000";

const resumeFile = document.getElementById('resumeFile');
const analyzeBtn = document.getElementById('analyzeBtn');
const spinner = document.getElementById('spinner');

const statSalary = document.getElementById('statSalary');
const statDemand = document.getElementById('statDemand');
const fitScore = document.getElementById('fitScore');
const fitComponents = document.getElementById('fitComponents');
const topSkillsEl = document.getElementById('topSkills');
const missingSkillsEl = document.getElementById('missingSkills');
const aiPlanEl = document.getElementById('aiPlan');
const jobListEl = document.getElementById('jobList');
const rawOutput = document.getElementById('rawOutput');

let salaryChart = null, skillChart = null;

function showSpinner(on){
  spinner.style.display = on ? 'inline-block' : 'none';
}

async function postResumeAndAnalyze(file){
  if(!file) { alert('Please select a resume file (PDF/DOCX/TXT)'); return; }
  showSpinner(true);

  // send file
  const fd = new FormData();
  fd.append('file', file, file.name);

  try {
    const resp = await fetch(`${API_BASE}/api/ai_full_analysis`, { method:'POST', body: fd });
    if(!resp.ok){
      const txt = await resp.text();
      throw new Error(`Server error ${resp.status}: ${txt}`);
    }
    const data = await resp.json();
    renderAll(data);
  } catch(err){
    console.error(err);
    alert('Analysis failed: ' + err.message);
  } finally {
    showSpinner(false);
  }
}

function numberFormat(n){ return n ? n.toLocaleString() : '—'; }

function makeSalaryChart(buckets, counts){
  const ctx = document.getElementById('chartSalaryDist').getContext('2d');
  if(salaryChart) salaryChart.destroy();
  salaryChart = new Chart(ctx, {
    type: 'bar',
    data: { labels: buckets, datasets: [{ label:'Count', data: counts }] },
    options: { plugins:{legend:{display:false}}, scales:{y:{beginAtZero:true}} }
  });
}

function makeSkillChart(required, matched){
  const ctx = document.getElementById('chartSkillMatch').getContext('2d');
  if(skillChart) skillChart.destroy();
  const labels = ['Matched','Missing'];
  const values = [matched, Math.max(0, required - matched)];
  skillChart = new Chart(ctx, {
    type: 'doughnut',
    data: { labels, datasets: [{ data: values }] },
    options: { plugins:{legend:{position:'bottom'}} }
  });
}

function renderAll(payload){
  // raw JSON
  rawOutput.textContent = JSON.stringify(payload, null, 2);

  // salary stats
  const s = payload.salary_range || {};
  statSalary.textContent = `Salary — Min: ₹${numberFormat(s.min)} Median: ₹${numberFormat(s.median)} Max: ₹${numberFormat(s.max)}`;

  // demand
  const ds = payload.demand_score ?? '—';
  statDemand.textContent = `Demand: ${ds}/100`;

  // fit score and components
  fitScore.textContent = (payload.resume_fit_score ?? '—') + '%';
  const comp = payload.components || {};
  fitComponents.textContent = `Skills: ${comp.skillComponent ?? '—'} | Demand: ${comp.demandComponent ?? '—'} | Salary: ${comp.salaryComponent ?? '—'}`;

  // skills
  topSkillsEl.textContent = (payload.required_skills && payload.required_skills.length) ? payload.required_skills.join(', ') : '—';
  missingSkillsEl.textContent = (payload.missing_skills && payload.missing_skills.length) ? payload.missing_skills.join(', ') : '—';

  // AI plan
  if(payload.ai_plan) {
    const p = payload.ai_plan;
    let html = '';
    if(p.priority && p.priority.length) html += `<div class="small-muted"><strong>Priority:</strong> ${p.priority.slice(0,3).join(', ')}</div>`;
    if(p.roadmap){
      for(const [k,v] of Object.entries(p.roadmap)){
        html += `<div style="margin-top:6px"><strong>${k}:</strong><div class="muted small">Steps: ${(v.steps||[]).join(' | ')}</div><div class="muted small">Resources: ${(v.resources||[]).slice(0,2).join(' | ')}</div></div>`;
      }
    }
    if(p.short_note) html += `<div style="margin-top:8px" class="muted small"><em>${p.short_note}</em></div>`;
    aiPlanEl.innerHTML = html || '<div class="muted small">—</div>';
  } else {
    aiPlanEl.innerHTML = '<div class="muted small">—</div>';
  }

  // job postings
  if(payload.jobs && payload.jobs.length){
    jobListEl.innerHTML = payload.jobs.slice(0,6).map(j => `<div><strong>${j.title}</strong> — ${j.company || ''} (${j.location || ''})</div>`).join('');
  } else {
    jobListEl.innerHTML = '<div class="muted small">No external job results (proxy missing) — showing synthetic data.</div>';
  }

  // charts: salary distribution (payload.salary_distribution: {labels:[],counts:[]})
  if(payload.salary_distribution && payload.salary_distribution.labels){
    makeSalaryChart(payload.salary_distribution.labels, payload.salary_distribution.counts);
  } else {
    // fallback synthetic
    makeSalaryChart(['0-3L','3-6L','6-9L','9-12L','12-15L'], [2,6,10,5,1]);
  }

  // skill match chart: required vs matched count
  const reqLen = (payload.required_skills||[]).length;
  const matched = (payload.matched_skills||[]).length;
  makeSkillChart(reqLen, matched);
}

analyzeBtn.addEventListener('click', async ()=> {
  const f = resumeFile.files[0];
  await postResumeAndAnalyze(f);
});

// allow pressing Enter while file input focused? Not necessary but optional
resumeFile.addEventListener('change', ()=> {
  // optionally auto-run analyze when file selected:
  // analyzeBtn.click();
});
