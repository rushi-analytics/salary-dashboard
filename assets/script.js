async function postResumeAndAnalyze(file){
  if(!file) { alert('Please select a resume file (PDF/DOCX/TXT)'); return; }
  showSpinner(true);

  const fd = new FormData();
  fd.append('resume', file, file.name);   // FIXED KEY NAME

  try {
    const resp = await fetch(`${API_BASE}/api/ai_full_analysis`, {
      method: 'POST',
      body: fd
    });

    if(!resp.ok){
      let text = await resp.text();
      throw new Error("Server error: " + text);
    }

    const data = await resp.json();
    renderAll(data);

  } catch(err){
    console.error(err);
    alert("Analysis failed: " + err.message);
  } finally {
    showSpinner(false);
  }
}
