import streamlit as st
import requests
import os

# Uses local API by default, or Render URL if deployed
API_URL = os.getenv("API_URL", "http://localhost:8000/api")

st.set_page_config(page_title="Exchange Agent Demo", layout="wide")
st.title("🎓 University Exchange AI")

default_prompt = '{"academic_profile": {"gpa": 85}, "preferences": {"vibe": "party"}}'
prompt = st.text_area("Enter Request (JSON format):", value=default_prompt, height=150)

if st.button("Run Agent"):
    if not prompt:
        st.warning("Please enter a prompt.")
    else:
        with st.spinner("Agent is reasoning..."):
            try:
                res = requests.post(f"{API_URL}/execute", json={"prompt": prompt})
                data = res.json()
                
                if data.get("status") == "ok":
                    st.success("### Final Recommendation")
                    st.write(data["response"])
                    
                    st.divider()
                    st.subheader("🛠 Execution Trace")
                    for step in data.get("steps", []):
                        with st.expander(f"Step: {step['module']}"):
                            st.write("**Prompt:**"); st.json(step["prompt"])
                            st.write("**Response:**"); st.json(step["response"])
                else:
                    st.error(f"Agent Error: {data.get('error')}")
            except Exception as e:
                st.error(f"System Error: {e}")
