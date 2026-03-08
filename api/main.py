from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
import uuid
import json
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Fez Exchange Agent API",
    description="University exchange recommendation AI agent"
)

agent = None

# PRODUCTION: strict initialization — mock fallback only in development/test mode
ENV_MODE = os.getenv("ENV_MODE", "production").lower()
ALLOW_MOCK = ENV_MODE in ("development", "test")

try:
    from orchestration.supervisor import Supervisor as RealSupervisor
    agent = RealSupervisor()
    logger.info("✅ Supervisor initialized successfully (REAL)")
except Exception as _init_err:
    logger.error("❌ Failed to initialize real Supervisor: %s", _init_err, exc_info=True)

    if ALLOW_MOCK:
        logger.warning("⚠️ ENV_MODE=%s: attempting mock fallback", ENV_MODE)
        try:
            from orchestration.mock_supervisor import Supervisor as MockSupervisor
            agent = MockSupervisor()
            logger.warning("⚠️ Using MockSupervisor (development/test only)")
        except Exception as _mock_err:
            logger.error("❌ Failed to initialize MockSupervisor: %s", _mock_err, exc_info=True)
            raise RuntimeError("Both real and mock supervisors failed")
    else:
        raise RuntimeError(
            f"Supervisor initialization failed in {ENV_MODE} mode. "
            "Set ENV_MODE=development or ENV_MODE=test to enable mock fallback."
        )

# ---------------- WEB UI ---------------- #

UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Fez Exchange Agent – Find Your Perfect University</title>
<style>
  /* ── Reset & Base ── */
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: #0f172a;
    color: #e2e8f0;
    min-height: 100vh;
    line-height: 1.6;
  }

  /* ── Layout ── */
  .container { max-width: 900px; margin: 0 auto; padding: 24px 20px 60px; }

  /* ── Hero Header ── */
  .hero {
    text-align: center;
    padding: 48px 24px 36px;
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-bottom: 1px solid #1e293b;
    margin-bottom: 32px;
  }
  .hero-badge {
    display: inline-block;
    background: #1d4ed8;
    color: #bfdbfe;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 4px 12px;
    border-radius: 999px;
    margin-bottom: 16px;
  }
  .hero h1 {
    font-size: clamp(26px, 5vw, 38px);
    font-weight: 800;
    color: #f1f5f9;
    margin-bottom: 12px;
  }
  .hero p {
    font-size: 16px;
    color: #94a3b8;
    max-width: 600px;
    margin: 0 auto 24px;
  }
  .how-to-steps {
    display: flex;
    justify-content: center;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 8px;
  }
  .step-pill {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 999px;
    padding: 6px 16px;
    font-size: 13px;
    color: #94a3b8;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .step-pill span.num {
    background: #3b82f6;
    color: white;
    border-radius: 50%;
    width: 20px;
    height: 20px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    flex-shrink: 0;
  }

  /* ── Card ── */
  .card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
  }
  .card-title {
    font-size: 14px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #64748b;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .card-title span { color: #3b82f6; }

  /* ── Examples ── */
  .examples-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 10px;
  }
  .example-btn {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 12px 14px;
    color: #e2e8f0;
    cursor: pointer;
    text-align: left;
    transition: border-color 0.15s, background 0.15s;
    font-size: 13px;
    line-height: 1.4;
  }
  .example-btn:hover { border-color: #3b82f6; background: #172033; }
  .example-btn strong { display: block; font-size: 13px; color: #93c5fd; margin-bottom: 4px; }
  .example-btn em { font-style: normal; color: #64748b; font-size: 12px; }

  /* ── Textarea + Button ── */
  .input-label {
    font-size: 13px;
    color: #94a3b8;
    margin-bottom: 8px;
  }
  textarea {
    width: 100%;
    height: 160px;
    background: #0f172a;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 13px;
    font-family: "SFMono-Regular", "Consolas", "Liberation Mono", monospace;
    resize: vertical;
    outline: none;
    transition: border-color 0.15s;
  }
  textarea:focus { border-color: #3b82f6; }
  .hint { font-size: 12px; color: #475569; margin-top: 6px; }

  .run-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 16px;
    padding: 12px 28px;
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
  }
  .run-btn:hover { background: #1d4ed8; }
  .run-btn:disabled { opacity: 0.55; cursor: not-allowed; }

  /* ── Spinner ── */
  .spinner {
    display: none;
    align-items: center;
    gap: 12px;
    color: #94a3b8;
    font-size: 14px;
    margin-top: 16px;
  }
  .spinner.active { display: flex; }
  .spin-ring {
    width: 20px; height: 20px;
    border: 3px solid #334155;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 0.75s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Results ── */
  #output { margin-top: 28px; }
  .results-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 10px;
  }
  .results-title {
    font-size: 20px;
    font-weight: 700;
    color: #f1f5f9;
  }
  .badge-count {
    background: #1d4ed8;
    color: #bfdbfe;
    border-radius: 999px;
    padding: 3px 12px;
    font-size: 12px;
    font-weight: 600;
  }

  /* University Card */
  .uni-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 20px;
  }
  .uni-header {
    background: linear-gradient(90deg, #1d4ed8 0%, #1e40af 100%);
    padding: 18px 22px;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
  }
  .uni-name { font-size: 20px; font-weight: 700; color: #fff; }
  .uni-rank {
    background: rgba(255,255,255,0.15);
    color: #bfdbfe;
    border-radius: 999px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
  }
  .uni-reasoning {
    padding: 14px 22px;
    font-size: 14px;
    color: #94a3b8;
    border-bottom: 1px solid #334155;
    font-style: italic;
  }
  .uni-body { padding: 22px; }

  .section-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #64748b;
    margin-bottom: 10px;
  }
  .req-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 10px;
    margin-bottom: 20px;
  }
  .req-item {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 10px 12px;
  }
  .req-item .req-key { font-size: 11px; color: #64748b; margin-bottom: 4px; }
  .req-item .req-val { font-size: 14px; font-weight: 600; color: #e2e8f0; }

  .logistics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
    margin-bottom: 20px;
  }
  .logistics-item {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 12px 14px;
  }
  .logistics-item .lg-icon { font-size: 20px; margin-bottom: 6px; }
  .logistics-item .lg-title { font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 4px; }
  .logistics-item .lg-val { font-size: 14px; color: #e2e8f0; }

  .courses-list { list-style: none; display: flex; flex-direction: column; gap: 6px; }
  .course-item {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 10px 14px;
    display: flex;
    align-items: flex-start;
    gap: 10px;
    font-size: 13px;
  }
  .course-item .lang-badge {
    background: #1e3a5f;
    color: #93c5fd;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 11px;
    font-weight: 600;
    white-space: nowrap;
    flex-shrink: 0;
    margin-top: 1px;
  }
  .course-item .course-name { color: #e2e8f0; font-weight: 500; }
  .course-item .course-rel { color: #64748b; font-size: 12px; margin-top: 2px; }

  /* Steps */
  .steps-section { margin-top: 28px; }
  .steps-title {
    font-size: 16px;
    font-weight: 700;
    color: #94a3b8;
    margin-bottom: 12px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    user-select: none;
  }
  .steps-title .toggle-icon { color: #475569; font-size: 12px; transition: transform 0.2s; }
  .steps-title.open .toggle-icon { transform: rotate(90deg); }
  .steps-list { display: none; }
  .steps-list.open { display: block; }
  .step-item {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    margin-bottom: 8px;
    overflow: hidden;
  }
  .step-header {
    padding: 10px 14px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 600;
    color: #94a3b8;
    user-select: none;
    transition: background 0.1s;
  }
  .step-header:hover { background: #263248; }
  .step-module-badge {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    color: #3b82f6;
  }
  .step-body {
    display: none;
    padding: 14px;
    border-top: 1px solid #334155;
  }
  .step-body.open { display: block; }
  .step-body pre {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 10px 12px;
    font-size: 12px;
    color: #94a3b8;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .step-sublabel { font-size: 11px; color: #475569; margin-bottom: 4px; margin-top: 8px; }

  /* Error banner */
  .error-banner {
    background: #450a0a;
    border: 1px solid #7f1d1d;
    border-radius: 8px;
    padding: 16px 20px;
    color: #fca5a5;
    font-size: 14px;
    display: flex;
    gap: 10px;
    align-items: flex-start;
  }

  /* Copy button */
  .copy-btn {
    background: transparent;
    border: 1px solid #334155;
    color: #94a3b8;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s;
  }
  .copy-btn:hover { border-color: #3b82f6; color: #93c5fd; }

  @media (max-width: 600px) {
    .hero { padding: 32px 16px 24px; }
    .container { padding: 16px 14px 40px; }
    .uni-header { flex-direction: column; }
  }
</style>
</head>
<body>

<!-- ── Hero ── -->
<div class="hero">
  <div class="hero-badge">AI-Powered Exchange Advisor</div>
  <h1>🎓 Find Your Perfect Exchange University</h1>
  <p>Describe your academic profile and preferences — our multi-agent AI will filter, rank, find matching courses, and analyze top universities for you.</p>
  <div class="how-to-steps">
    <div class="step-pill"><span class="num">1</span> Pick an example or write your profile</div>
    <div class="step-pill"><span class="num">2</span> Click <strong>Run Agent</strong></div>
    <div class="step-pill"><span class="num">3</span> Browse recommendations below</div>
  </div>
</div>

<div class="container">

  <!-- ── Input Card ── -->
  <div class="card">
    <div class="card-title"><span>⚡</span> Quick Examples</div>
    <div class="examples-grid">
      <button class="example-btn" onclick="loadExample('cs_nightlife')">
        <strong>💻 CS + Nightlife</strong>
        <em>Computer Science, GPA 3.2, party vibe</em>
      </button>
      <button class="example-btn" onclick="loadExample('business_budget')">
        <strong>📊 Business + Budget</strong>
        <em>Business, GPA 3.0, affordable cities</em>
      </button>
      <button class="example-btn" onclick="loadExample('engineering_culture')">
        <strong>⚙️ Engineering + Culture</strong>
        <em>Electrical Eng., GPA 2.9, culture & history</em>
      </button>
      <button class="example-btn" onclick="loadExample('cs_english')">
        <strong>🌍 CS + English-only</strong>
        <em>Computer Science, GPA 3.1, English courses</em>
      </button>
    </div>
  </div>

  <div class="card">
    <div class="card-title"><span>✏️</span> Your Profile</div>
    <p class="input-label">Paste a JSON profile or type a free-text message (e.g. "show me something cheaper"):</p>
    <textarea id="prompt" placeholder='{"academic_profile":{"gpa":3.2,"major":"Computer Science"},"preferences":{"free_language_preferences":"nightlife, affordable"}}'>{"academic_profile":{"gpa":3.2,"major":"Computer Science"},"preferences":{"free_language_preferences":"nightlife, affordable"}}</textarea>
    <p class="hint">💡 Tip: Use <strong>gpa</strong> (0.0–4.0 scale), <strong>major</strong>, and <strong>free_language_preferences</strong> for best results. Follow-ups like "show more" or "find something cheaper" also work.</p>
    <button class="run-btn" id="runBtn" onclick="runAgent()">
      <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
      Run Agent
    </button>
    <div class="spinner" id="spinner">
      <div class="spin-ring"></div>
      <span id="spinnerText">Initializing agents…</span>
    </div>
  </div>

  <!-- ── Output ── -->
  <div id="output"></div>

</div>

<script>
const EXAMPLES = {
  cs_nightlife: JSON.stringify({
    academic_profile: { gpa: 3.2, major: "Computer Science" },
    preferences: { free_language_preferences: "nightlife, party vibe, easy to make friends" }
  }, null, 2),
  business_budget: JSON.stringify({
    academic_profile: { gpa: 3.0, major: "Business Administration" },
    preferences: { free_language_preferences: "affordable, low cost of living, budget friendly" }
  }, null, 2),
  engineering_culture: JSON.stringify({
    academic_profile: { gpa: 2.9, major: "Electrical Engineering" },
    preferences: { free_language_preferences: "culture, history, museums, beautiful city" }
  }, null, 2),
  cs_english: JSON.stringify({
    academic_profile: { gpa: 3.1, major: "Computer Science" },
    preferences: { free_language_preferences: "English spoken environment, international community" },
    language_profile: { english_only: true }
  }, null, 2)
};

function loadExample(key) {
  document.getElementById("prompt").value = EXAMPLES[key];
}

const SPINNER_MESSAGES = [
  "Filtering eligible universities…",
  "Ranking by your preferences…",
  "Finding matching courses…",
  "Analyzing logistics & housing…",
  "Almost there…"
];
let spinnerInterval = null;

function startSpinner() {
  const btn = document.getElementById("runBtn");
  const spinner = document.getElementById("spinner");
  const spinnerText = document.getElementById("spinnerText");
  btn.disabled = true;
  spinner.classList.add("active");
  let i = 0;
  spinnerText.textContent = SPINNER_MESSAGES[0];
  spinnerInterval = setInterval(() => {
    i = (i + 1) % SPINNER_MESSAGES.length;
    spinnerText.textContent = SPINNER_MESSAGES[i];
  }, 3500);
}

function stopSpinner() {
  clearInterval(spinnerInterval);
  document.getElementById("runBtn").disabled = false;
  document.getElementById("spinner").classList.remove("active");
}

function esc(str) {
  return String(str ?? "")
    .replace(/&/g,"&amp;")
    .replace(/</g,"&lt;")
    .replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;");
}

function renderReqGrid(reqs) {
  if (!reqs || typeof reqs !== "object") return "";
  const items = [
    { key: "Min GPA", val: reqs.min_gpa ?? "—" },
    { key: "Erasmus", val: reqs.erasmus_available ? "✅ Yes" : "❌ No" },
    { key: "English Req", val: reqs.english_test_level || "None" },
    { key: "Min Semesters", val: reqs.min_semesters_completed ?? "—" },
  ];
  return `<div class="section-label">📋 Hard Requirements</div>
  <div class="req-grid">
    ${items.map(i => `<div class="req-item"><div class="req-key">${esc(i.key)}</div><div class="req-val">${esc(i.val)}</div></div>`).join("")}
  </div>`;
}

function renderLogistics(logistics) {
  if (!logistics || typeof logistics !== "object") return "";
  const acad = logistics.academic || {};
  const hous = logistics.housing_and_logistics || {};
  const intg = logistics.student_integration || {};
  const items = [
    { icon: "📚", title: "Credits", val: acad.min_credits_required != null ? `${acad.min_credits_required} – ${acad.max_credits_allowed ?? "?"}` : "—" },
    { icon: "🏠", title: "Living Cost / Month", val: hous.estimated_living_cost_per_month ? `${hous.estimated_living_cost_per_month} ${hous.currency || ""}` : "—" },
    { icon: "🤝", title: "Buddy Program", val: intg.buddy_program_available ? "✅ Available" : "❌ Not available" },
  ];
  return `<div class="section-label" style="margin-top:16px">🏘️ Logistics & Student Experience</div>
  <div class="logistics-grid">
    ${items.map(i => `<div class="logistics-item"><div class="lg-icon">${i.icon}</div><div class="lg-title">${esc(i.title)}</div><div class="lg-val">${esc(i.val)}</div></div>`).join("")}
  </div>`;
}

function renderCourses(courses) {
  if (!courses || courses.length === 0) return "";
  return `<div class="section-label" style="margin-top:16px">📖 Matched Courses (${courses.length})</div>
  <ul class="courses-list">
    ${courses.map(c => `<li class="course-item">
      <span class="lang-badge">${esc(c.language || "EN")}</span>
      <div><div class="course-name">${esc(c.course_name || c.name || "")}</div><div class="course-rel">${esc(c.relevance || "")}</div></div>
    </li>`).join("")}
  </ul>`;
}

function renderUniversities(universities, coursesByUni) {
  if (!universities.length) return `<div class="card"><p style="color:#64748b;text-align:center">No universities matched your profile. Try adjusting your GPA or preferences.</p></div>`;
  return universities.map((uni, idx) => {
    const courses = coursesByUni[uni.university_name] || [];
    return `<div class="uni-card">
      <div class="uni-header">
        <div class="uni-name">🏛️ ${esc(uni.university_name)}</div>
        <div class="uni-rank">#${idx + 1} Match</div>
      </div>
      ${uni.general_fit_reasoning ? `<div class="uni-reasoning">${esc(uni.general_fit_reasoning)}</div>` : ""}
      <div class="uni-body">
        ${renderReqGrid(uni.requirements)}
        ${renderLogistics(uni.logistics)}
        ${renderCourses(courses)}
      </div>
    </div>`;
  }).join("");
}

function renderSteps(steps) {
  if (!steps || !steps.length) return "";
  const stepsHtml = steps.map((s, i) => `
    <div class="step-item">
      <div class="step-header" onclick="toggleStep(this)">
        <span class="step-module-badge">${esc(s.module || "Step")}</span>
        <span>Step ${i + 1}</span>
      </div>
      <div class="step-body">
        <div class="step-sublabel">PROMPT</div>
        <pre>${esc(JSON.stringify(s.prompt, null, 2))}</pre>
        <div class="step-sublabel">RESPONSE</div>
        <pre>${esc(JSON.stringify(s.response, null, 2))}</pre>
      </div>
    </div>`).join("");
  return `<div class="steps-section">
    <div class="steps-title" onclick="toggleSteps(this)">
      <span class="toggle-icon">▶</span> Execution Trace (${steps.length} steps)
    </div>
    <div class="steps-list">${stepsHtml}</div>
  </div>`;
}

function toggleSteps(el) {
  el.classList.toggle("open");
  el.nextElementSibling.classList.toggle("open");
}
function toggleStep(el) {
  el.nextElementSibling.classList.toggle("open");
}

async function runAgent() {
  const prompt = document.getElementById("prompt").value.trim();
  if (!prompt) return;
  startSpinner();
  document.getElementById("output").innerHTML = "";

  try {
    const res = await fetch("/api/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt })
    });
    const data = await res.json();
    stopSpinner();

    if (data.status === "error") {
      document.getElementById("output").innerHTML = `<div class="error-banner">⚠️ <div><strong>Agent Error</strong><br>${esc(data.error || "Unknown error")}</div></div>`;
      return;
    }

    let parsed = {};
    try { parsed = JSON.parse(data.response || "{}"); } catch(_) {}
    const universities = Array.isArray(parsed) ? parsed : (parsed.analysis || []);
    const coursesList = parsed.courses || [];
    const coursesByUni = {};
    coursesList.forEach(c => { coursesByUni[c.university_name] = c.matched_courses || []; });

    const uniHtml = renderUniversities(universities, coursesByUni);
    const stepsHtml = renderSteps(data.steps || []);

    const copyId = "json_raw_" + Date.now();
    const rawJson = JSON.stringify({ analysis: universities, courses: coursesList }, null, 2);

    document.getElementById("output").innerHTML = `
      <div class="results-header">
        <div class="results-title">🎯 Recommendations</div>
        <div style="display:flex;gap:8px;align-items:center">
          <span class="badge-count">${universities.length} Universit${universities.length === 1 ? "y" : "ies"}</span>
          <button class="copy-btn" onclick="copyJson('${copyId}')">📋 Copy JSON</button>
        </div>
      </div>
      <textarea id="${copyId}" style="position:absolute;left:-9999px;top:-9999px" readonly>${esc(rawJson)}</textarea>
      ${uniHtml}
      ${stepsHtml}`;
  } catch (err) {
    stopSpinner();
    document.getElementById("output").innerHTML = `<div class="error-banner">⚠️ <div><strong>Network Error</strong><br>${esc(String(err))}</div></div>`;
  }
}

function copyJson(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.select();
  document.execCommand("copy");
  const btn = document.querySelector(".copy-btn");
  if (btn) { const orig = btn.textContent; btn.textContent = "✅ Copied!"; setTimeout(() => btn.textContent = orig, 2000); }
}
</script>

</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def serve_ui():
    return UI_HTML


# ---------------- REQUEST SCHEMAS ---------------- #

class ExecuteRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None


class StepLog(BaseModel):
    module: str
    prompt: Dict[str, Any]
    response: Dict[str, Any]


class ExecuteResponse(BaseModel):
    status: str
    session_id: Optional[str] = None
    error: Optional[str] = None
    response: Optional[Any] = None
    steps: List[StepLog] = []


# ---------------- REQUIRED ENDPOINTS ---------------- #

@app.get("/api/team_info")
def get_team_info():
    return {
        "group_batch_order_number": "01_01",
        "team_name": "Fez Exchange Agent",
        "students": [
            {
                "name": "Yam Ben Tob",
                "email": "yam.b@campus.technion.ac.il"
            },
            {
                "name": "Asaf Greenstein",
                "email": "asaf.g@campus.technion.ac.il"
            },
            {
                "name": "Anna Sakoun",
                "email": "anna.sakoun@campus.technion.ac.il"
            }
        ]
    }


@app.get("/api/agent_info")
def get_agent_info():
    return {
        "description": "Conversation-aware multi-agent orchestration system for global university exchange placement. Uses Filter (Supabase), Ranker (LLM), CourseFinder (ReAct + RAG + Web), and Analyzer (Pinecone RAG + LLM) to recommend universities and matched courses.",

        "purpose": "Filters universities by academic/language/availability criteria, ranks by preferences, finds courses, and analyzes top matches for logistics and fit. Supports follow-up prompts such as 'show more', 'find courses', or 'something cheaper'.",

        "prompt_template": {
            "template": '{"academic_profile":{"gpa":3.2,"major":"Computer Science"},"preferences":{"free_language_preferences":"social scene, party vibe"},"language_profile":{},"availability":{}}'
        },

        "prompt_examples": [
            {
                "prompt": '{"academic_profile":{"gpa":3.2},"preferences":{"free_language_preferences":"party vibe, easy to make friends"}}',

                "full_response": "The agent recommends universities such as CTU Prague, DTU, and Politecnico di Milano because they combine strong computer science programs with vibrant student life.",

                "steps": [

                    {
                        "module": "Filter",
                        "prompt": {
                            "action": "Query Supabase",
                            "criteria": "user academic profile"
                        },
                        "response": {
                            "found_universities": 12
                        }
                    },

                    {
                        "module": "Ranker",
                        "prompt": {
                            "llm_prompt": "Rank universities based on social life and academic strength"
                        },
                        "response": {
                            "top_universities": [
                                "CTU Prague",
                                "DTU",
                                "Politecnico di Milano"
                            ]
                        }
                    },

                    {
                        "module": "CourseFinder",
                        "prompt": {
                            "universities": ["CTU Prague"],
                            "major": "Computer Science"
                        },
                        "response": {
                            "courses_found": 5,
                            "courses": [
                                "Algorithms",
                                "Machine Learning",
                                "Data Structures"
                            ]
                        }
                    },

                    {
                        "module": "Analyzer",
                        "prompt": {
                            "target_university": "CTU Prague"
                        },
                        "response": {
                            "logistics": {
                                "housing": "student dorm lottery",
                                "estimated_cost": "3500 USD per semester"
                            }
                        }
                    }

                ]
            }
        ]
    }


@app.get("/api/model_architecture")
def get_architecture():
    base = os.path.dirname(os.path.abspath(__file__))

    # Check locations in priority order.
    # docs/architecture.png is the canonical stable path per architecture guidelines.
    for rel_path in (
        os.path.join("..", "docs", "architecture.png"),
        os.path.join("..", "architecture.png"),
        os.path.join("..", "architecture_placeholder.png"),
    ):
        file_path = os.path.join(base, rel_path)

        if os.path.exists(file_path):
            return FileResponse(file_path, media_type="image/png")

    raise HTTPException(status_code=404, detail="Image not found")


@app.post("/api/execute", response_model=ExecuteResponse)
def execute_agent(request: ExecuteRequest):
    logger.debug("[execute] Received prompt: %.200s", request.prompt)

    if agent is None:
        logger.error("[execute] Agent is not initialized")
        return {
            "status": "error",
            "error": "Agent failed to initialize at startup. Check server logs.",
            "response": None,
            "steps": []
        }

    try:

        try:
            user_profile = json.loads(request.prompt)
            chat_msg = ""
            logger.debug("[execute] Parsed JSON profile with keys: %s", list(user_profile.keys()))

        except json.JSONDecodeError:
            user_profile = {}
            chat_msg = request.prompt
            logger.debug("[execute] Using free-text prompt: %.100s", chat_msg)

        logger.debug("[execute] Invoking supervisor...")
        session_id = request.session_id if request.session_id else str(uuid.uuid4())
        result = agent.run(
            new_chat_message=chat_msg,
            user_profile_dict=user_profile,
            thread_id=session_id
        )

        analysis = result.get("analysis", [])
        courses = result.get("courses", [])
        steps = result.get("steps", [])
        logger.debug("[execute] analysis=%d items, courses=%d items, steps=%d items",
                     len(analysis) if isinstance(analysis, list) else 0,
                     len(courses) if isinstance(courses, list) else 0,
                     len(steps) if isinstance(steps, list) else 0)

        response_payload = json.dumps({
            "analysis": analysis,
            "courses": courses
        })

        return {
            "status": "ok",
            "session_id": session_id,
            "error": None,
            "response": response_payload,
            "steps": steps
        }

    except Exception as e:
        logger.error("[execute] Unhandled error: %s", e, exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "response": None,
            "steps": []
        }


# ---------------- RUN SERVER ---------------- #

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
