import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.title("AI Career Coach 🤖")

if "user_id" not in st.session_state:
    st.session_state.user_id = None

st.sidebar.header("Upload Resume")
resume_file = st.sidebar.file_uploader("Upload your resume (PDF/DOCX)")

if resume_file and st.sidebar.button("Upload & Analyze"):
    files = {"file": resume_file}
    data = {}
    resp = requests.post(f"{API_URL}/upload_resume/", files=files, data=data)
    if resp.ok:
        res = resp.json()
        st.session_state.user_id = res["user_id"]
        st.success("Resume processed successfully!")
        st.json(res["parsed_resume"])

if st.session_state.user_id:
    st.subheader("Chat with your AI Coach")
    user_msg = st.text_input("Ask something about your career, interview prep, or resume")
    if st.button("Send") and user_msg:
        resp = requests.post(f"{API_URL}/chat/{st.session_state.user_id}", json={"message": user_msg})
        if resp.ok:
            st.markdown(f"**Coach:** {resp.json()['answer']}")
