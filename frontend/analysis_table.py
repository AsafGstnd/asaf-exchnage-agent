import streamlit as st
import json
import requests
import os
import pandas as pd
from tests.user_profiles import get_student_profiles
from orchestration.supervisor import Supervisor

# --- SETTINGS ---
_use_api_env = os.getenv("USE_API", "").lower() in ("true", "1", "yes")
API_URL_DEFAULT = os.getenv("API_URL", "http://localhost:8000/api")

st.set_page_config(
    page_title="Fez Exchange Agent – Find Your University",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Minimal global style tweaks ──
st.markdown("""
<style>
/* Tighten hero section */
.hero-block { padding: 0.5rem 0 1.5rem 0; }
/* Compact metric cards */
div[data-testid="metric-container"] { background:#1e293b; border-radius:8px; padding:12px 16px; }
/* Improve expander spacing */
div[data-testid="stExpander"] { border: 1px solid #334155 !important; border-radius:8px !important; }
</style>
""", unsafe_allow_html=True)

# ── Hero ──
st.markdown('<div class="hero-block">', unsafe_allow_html=True)
st.title("🎓 Find Your Perfect Exchange University")
st.caption(
    "Our multi-agent AI **filters** universities by your academic profile, "
    "**ranks** them by your lifestyle preferences, **finds matching courses**, "
    "and **analyzes** logistics for the top results."
)
st.markdown('</div>', unsafe_allow_html=True)

# ── Pre-built example profiles ──
EXAMPLE_PROFILES = {
    "💻 CS + Nightlife": {
        "academic_profile": {"gpa": 3.2, "major": "Computer Science"},
        "preferences": {"free_language_preferences": "nightlife, party vibe, easy to make friends"}
    },
    "📊 Business + Budget": {
        "academic_profile": {"gpa": 3.0, "major": "Business Administration"},
        "preferences": {"free_language_preferences": "affordable, low cost of living, budget friendly"}
    },
    "⚙️ Engineering + Culture": {
        "academic_profile": {"gpa": 2.9, "major": "Electrical Engineering"},
        "preferences": {"free_language_preferences": "culture, history, museums, beautiful city"}
    },
    "🌍 CS + English-only": {
        "academic_profile": {"gpa": 3.1, "major": "Computer Science"},
        "preferences": {"free_language_preferences": "English spoken environment, international community"},
        "language_profile": {"english_only": True}
    },
}

# --- Sidebar ---
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.divider()

    # API mode
    use_api = st.checkbox(
        "Use deployed API",
        value=_use_api_env,
        help="Call the deployed Render server instead of running the agent locally. "
             "Set USE_API=true and API_URL in your environment for the hosted URL."
    )
    if use_api:
        api_url = st.text_input(
            "API URL",
            value=API_URL_DEFAULT,
            help="e.g. https://your-app.onrender.com/api"
        )
    else:
        api_url = API_URL_DEFAULT

    st.divider()

    # Quick example buttons
    st.markdown("### 🚀 Quick Examples")
    st.caption("Click any profile to load it into the editor below.")
    for label, profile in EXAMPLE_PROFILES.items():
        if st.button(label, use_container_width=True, key=f"ex_{label}"):
            st.session_state["profile_text"] = json.dumps(profile, indent=4)

    st.divider()

    # Input area
    st.markdown("### ✏️ Your Profile")
    st.caption(
        "Paste a **JSON profile** or type a **free-text follow-up** "
        "(e.g. *\"show me something cheaper\"* or *\"find more universities\"*)."
    )

    default_profile = json.dumps(
        get_student_profiles().get("default", EXAMPLE_PROFILES["💻 CS + Nightlife"]),
        indent=4
    )
    raw_user_str = st.text_area(
        "Profile / Message",
        value=st.session_state.get("profile_text", default_profile),
        height=360,
        label_visibility="collapsed",
        placeholder='{"academic_profile": {"gpa": 3.2, "major": "Computer Science"}, ...}'
    )

    with st.expander("📖 JSON Format Guide"):
        st.markdown("""
```json
{
  "academic_profile": {
    "gpa": 3.2,
    "major": "Computer Science"
  },
  "preferences": {
    "free_language_preferences": "nightlife, affordable"
  },
  "language_profile": {
    "english_only": true
  },
  "availability": {
    "semester": "fall",
    "year": 2025
  }
}
```
**Key fields:**
- `gpa` — score on **0.0–4.0** scale (USA standard)
- `major` — your field of study
- `free_language_preferences` — lifestyle keywords
        """)

    run_button = st.button("🔍 Run Agent", use_container_width=True, type="primary")

USE_API = use_api
API_URL = api_url

# Initialize local agent
if not USE_API:
    if Supervisor is None:
        st.error("Supervisor class could not be imported. Enable 'Use deployed API' or fix local imports.")
    elif "agent" not in st.session_state:
        with st.spinner("Initializing local agent…"):
            st.session_state.agent = Supervisor()

# --- Main Logic ---
if run_button:
    with st.spinner("🤖 Agents at work — this may take up to 2 minutes…"):
        try:
            # ==========================================
            # 1. DATA FETCHING (Local vs Server)
            # ==========================================
            if USE_API:
                res = requests.post(f"{API_URL}/execute", json={"prompt": raw_user_str})
                data = res.json()

            else:
                try:
                    user_profile = json.loads(raw_user_str)
                    chat_msg = ""
                except json.JSONDecodeError:
                    user_profile = {}
                    chat_msg = raw_user_str

                try:
                    result = st.session_state.agent.run(
                        new_chat_message=chat_msg,
                        user_profile_dict=user_profile
                    )
                    payload = {"analysis": result.get("analysis", []), "courses": result.get("courses", [])}
                    data = {
                        "status": "ok",
                        "error": None,
                        "response": json.dumps(payload),
                        "steps": result.get("steps", [])
                    }
                except Exception as local_e:
                    data = {
                        "status": "error",
                        "error": str(local_e),
                        "response": "[]",
                        "steps": []
                    }

            # ==========================================
            # 2. UI RENDERING
            # ==========================================
            if data.get("status") == "ok":

                raw_response_string = data.get("response", "{}")
                try:
                    parsed = json.loads(raw_response_string)
                    if isinstance(parsed, list):
                        universities = parsed
                        courses_list = []
                    else:
                        universities = parsed.get("analysis", [])
                        courses_list = parsed.get("courses", [])
                except json.JSONDecodeError:
                    universities = []
                    courses_list = []
                    st.warning("⚠️ Could not parse the agent response.")

                courses_by_university = {
                    c.get("university_name", ""): c.get("matched_courses", [])
                    for c in courses_list
                }
                agent_steps = data.get("steps", [])

                # ── Summary banner ──
                if universities:
                    st.success(
                        f"✅ Analysis complete! Found **{len(universities)}** matching "
                        f"universit{'y' if len(universities) == 1 else 'ies'}."
                    )
                else:
                    st.warning("No universities matched your profile. Try lowering your GPA requirement or broadening your preferences.")

                # ── University tabs ──
                if universities:
                    uni_names = [u.get("university_name", f"University {i+1}") for i, u in enumerate(universities)]
                    tabs = st.tabs([f"#{i+1} {n}" for i, n in enumerate(uni_names)])

                    for i, tab in enumerate(tabs):
                        uni = universities[i]
                        reqs = uni.get("requirements", {})
                        logistics = uni.get("logistics", {})
                        acad = logistics.get("academic", {})
                        hous = logistics.get("housing_and_logistics", {})
                        intg = logistics.get("student_integration", {})

                        with tab:
                            # Fit reasoning
                            reasoning = uni.get("general_fit_reasoning", "")
                            if reasoning:
                                st.info(f"💡 {reasoning}")

                            st.markdown("---")
                            st.markdown("#### 📋 Hard Requirements")

                            # Metrics row
                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("Min GPA", reqs.get("min_gpa", "—"))
                            m2.metric("Erasmus", "✅ Yes" if reqs.get("erasmus_available") else "❌ No")
                            m3.metric("English Req", reqs.get("english_test_level") or "None")
                            m4.metric("Min Semesters", reqs.get("min_semesters_completed", "—"))

                            # Calendar
                            fall = reqs.get("fall_semester", {})
                            if fall:
                                st.caption(
                                    f"📅 Fall: {fall.get('start_month', '?')}/{fall.get('start_day', '?')} "
                                    f"→ {fall.get('end_month', '?')}/{fall.get('end_day', '?')}"
                                )

                            st.markdown("---")
                            st.markdown("#### 🏘️ Logistics & Student Experience")

                            l1, l2, l3 = st.columns(3)

                            with l1:
                                st.markdown("**📚 Academic**")
                                credits_min = acad.get("min_credits_required")
                                credits_max = acad.get("max_credits_allowed")
                                if credits_min is not None:
                                    st.metric("Credits Range", f"{credits_min} – {credits_max or '?'}")
                                with st.expander("Academic Notes"):
                                    st.write(acad.get("academic_summary_notes") or "No notes available.")

                            with l2:
                                st.markdown("**🏠 Cost & Housing**")
                                cost = hous.get("estimated_living_cost_per_month")
                                currency = hous.get("currency", "")
                                if cost:
                                    st.metric("Living Cost / Month", f"{cost} {currency}".strip())
                                with st.expander("Housing Details"):
                                    st.write(hous.get("housing_details") or "No details available.")

                            with l3:
                                st.markdown("**🤝 Integration**")
                                buddy = intg.get("buddy_program_available")
                                st.metric("Buddy Program", "✅ Available" if buddy else "❌ Not available")
                                with st.expander("Integration Notes"):
                                    st.write(intg.get("integration_summary_notes") or "No notes available.")

                            # Matched courses
                            matched_courses = courses_by_university.get(uni.get("university_name", ""), [])
                            if matched_courses:
                                st.markdown("---")
                                st.markdown(f"#### 📖 Matched Courses ({len(matched_courses)})")
                                courses_data = [
                                    {
                                        "Course": c.get("course_name", ""),
                                        "Language": c.get("language", ""),
                                        "Relevance": c.get("relevance", "")
                                    }
                                    for c in matched_courses
                                ]
                                st.dataframe(
                                    pd.DataFrame(courses_data),
                                    hide_index=True,
                                    use_container_width=True
                                )

                # Execution trace
                st.markdown("---")
                with st.expander(f"🛠️ Execution Trace ({len(agent_steps)} steps)", expanded=False):
                    if agent_steps:
                        for step in agent_steps:
                            module = step.get("module", "Unknown")
                            st.markdown(f"**Module: `{module}`**")
                            c1, c2 = st.columns(2)
                            with c1:
                                st.caption("Prompt")
                                st.json(step.get("prompt", {}))
                            with c2:
                                st.caption("Response")
                                st.json(step.get("response", {}))
                            st.divider()
                    else:
                        st.caption("No execution steps recorded.")

            elif data.get("status") == "error":
                st.error(f"❌ Agent Error: {data.get('error')}")

        except Exception as e:
            st.error(f"❌ System Error: {e}")

# ── Empty state guidance ──
else:
    st.markdown("---")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("#### 1️⃣ Choose a Profile")
        st.caption("Click a **Quick Example** in the sidebar, or paste your own JSON profile into the editor.")
    with col_b:
        st.markdown("#### 2️⃣ Run the Agent")
        st.caption("Hit **🔍 Run Agent** and wait ~30–90 seconds while the AI pipeline runs.")
    with col_c:
        st.markdown("#### 3️⃣ Explore Results")
        st.caption("Browse university tabs, review requirements, logistics, and matched courses.")
