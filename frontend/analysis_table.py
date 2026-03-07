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

st.set_page_config(page_title="Exchange Agent Pro", layout="wide")
st.title("🎓 University Selection Dashboard")

# --- Sidebar: API mode toggle and input ---
with st.sidebar:
    use_api = st.checkbox("Use deployed API", value=_use_api_env, help="Call deployed server. Set USE_API=true and API_URL for your Render URL.")
    if use_api:
        api_url = st.text_input("API URL", value=API_URL_DEFAULT, help="e.g. https://your-app.onrender.com/api")
    else:
        api_url = API_URL_DEFAULT
USE_API = use_api
API_URL = api_url

# Initialize local agent in session state so it remembers memory between clicks
if not USE_API:
    if Supervisor is None:
        st.error("Supervisor class could not be imported. Enable 'Use deployed API' or fix local imports.")
    elif "agent" not in st.session_state:
        st.session_state.agent = Supervisor()

# --- Sidebar Input ---
with st.sidebar:
    st.header("Search Settings")
    user_dict = get_student_profiles().get("default", {})
    formatted_user_str = json.dumps(user_dict, indent=4)
    raw_user_str = st.text_area(
        "User Profile (JSON) or Chat Message:", 
        value=formatted_user_str, 
        height=400
    )
    run_button = st.button("Run Agent", use_container_width=True)

# --- Main Logic ---
if run_button:
    with st.spinner("Analyzing universities..."):
        try:
            # ==========================================
            # 1. DATA FETCHING (Local vs Server)
            # ==========================================
            if USE_API:
                # --- SERVER RUN ---
                # The API returns "response" as a stringified JSON to satisfy the strict rubric
                res = requests.post(f"{API_URL}/execute", json={"prompt": raw_user_str})
                data = res.json()
                
            else:
                # --- LOCAL RUN ---
                # Replicate the exact routing logic from your FastAPI endpoint
                try:
                    user_profile = json.loads(raw_user_str)
                    chat_msg = "" 
                except json.JSONDecodeError:
                    user_profile = {}
                    chat_msg = raw_user_str
                
                try:
                    # Run the agent directly. result["analysis"] is a Python list of dicts.
                    result = st.session_state.agent.run(
                        new_chat_message=chat_msg, 
                        user_profile_dict=user_profile
                    )
                    
                    # MOCK THE API EXACTLY: Convert the native Python list into a string
                    # so the downstream UI code handles local and server data identically!
                    payload = {"analysis": result.get("analysis", []), "courses": result.get("courses", [])}
                data = {
                        "status": "ok",
                        "error": None,
                        "response": json.dumps(payload),
                        "steps": result.get("steps", [])
                    }
                except Exception as local_e:
                    # Mock an API error format if the agent crashes locally
                    data = {
                        "status": "error",
                        "error": str(local_e),
                        "response": "[]",
                        "steps": []
                    }

            # ==========================================
            # 2. UI RENDERING (Identical for both modes)
            # ==========================================
            
            # Check the exact status field required by your rubric
            if data.get("status") == "ok":
                
                # --- DESERIALIZE THE RESPONSE ---
                # Response is JSON: {"analysis": [...], "courses": [...]}
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
                    st.warning("Could not parse the response.")
                courses_by_university = {
                    c.get("university_name", ""): c.get("matched_courses", [])
                    for c in courses_list
                }
                agent_steps = data.get("steps", [])
                
                st.success(f"Analysis Complete! Found {len(universities)} matches.")
                
                # --- BUILD THE NICE TABLES ---
                if universities:
                    uni_names = [u.get("university_name", "Unknown") for u in universities]
                    tabs = st.tabs(uni_names)
                    
                    for i, tab in enumerate(tabs):
                        uni = universities[i]
                        # Accessing our Buckets
                        reqs = uni.get("requirements", {})
                        logistics = uni.get("logistics", {})
                        
                        with tab:
                            st.info(uni.get("general_fit_reasoning", "No reasoning provided."))
                            
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                st.markdown("#### ✅ Hard Requirements")
                                elig_data = {
                                    "Min GPA": reqs.get("min_gpa"),
                                    "Erasmus?": "✅ Yes" if reqs.get("erasmus_available") else "❌ No",
                                    "English Req": reqs.get("english_test_level", "N/A"),
                                    "Min Semesters": reqs.get("min_semesters_completed")
                                }
                                st.dataframe(pd.DataFrame([elig_data]), hide_index=True)
                                
                            with col2:
                                st.markdown("#### 📅 Calendar")
                                fall = reqs.get("fall_semester", {})
                                st.write(f"**Fall:** {fall.get('start_month')}/{fall.get('start_day')} - {fall.get('end_month')}/{fall.get('end_day')}")
                            
                            st.divider()
                            st.markdown("### 🏘️ Logistics & Student Experience")
                            
                            l_col1, l_col2, l_col3 = st.columns(3)
                            with l_col1:
                                st.subheader("📚 Academic")
                                st.write(f"**Credits:** {logistics.get('academic', {}).get('min_credits_required')} - {logistics.get('academic', {}).get('max_credits_allowed')}")
                                with st.expander("Notes"):
                                    st.write(logistics.get("academic", {}).get("academic_summary_notes", "N/A"))
                            with l_col2:
                                st.subheader("🏠 Cost & Housing")
                                st.write(f"**Living Cost:** {logistics.get('housing_and_logistics', {}).get('estimated_living_cost_per_month')} {logistics.get('housing_and_logistics', {}).get('currency')}")
                                with st.expander("Details"):
                                    st.write(logistics.get("housing_and_logistics", {}).get("housing_details", "N/A"))
                            with l_col3:
                                st.subheader("🤝 Integration")
                                st.write(f"**Buddy Program:** {'✅' if logistics.get('student_integration', {}).get('buddy_program_available') else '❌'}")
                                with st.expander("Details"):
                                    st.write(logistics.get("student_integration", {}).get("integration_summary_notes", "N/A"))

                            # --- MATCHED COURSES ---
                            matched_courses = courses_by_university.get(uni.get("university_name", ""), [])
                            if matched_courses:
                                st.divider()
                                st.markdown("### 📚 Matched Courses")
                                courses_data = [
                                    {
                                        "Course": c.get("course_name", ""),
                                        "Language": c.get("language", ""),
                                        "Relevance": c.get("relevance", "")
                                    }
                                    for c in matched_courses
                                ]
                                st.dataframe(pd.DataFrame(courses_data), hide_index=True, use_container_width=True)
                                
                # --- BUILD THE REQUIRED TRACE ---
                st.divider()
                st.subheader("🛠 Execution Trace")
                for step in agent_steps:
                    with st.expander(f"Module: {step.get('module', 'Unknown')}"):
                        st.write("**Prompt:**")
                        st.json(step.get("prompt", {}))
                        st.write("**Response:**")
                        st.json(step.get("response", {}))
                        
            # Handle the exact error format expected by your API requirements
            elif data.get("status") == "error":
                st.error(f"Agent Error: {data.get('error')}")
                
        except Exception as e:
            st.error(f"System Error: {e}")