import streamlit as st
import utils
import os

st.title("⚙️ Settings & Rules")

# Section 1: Gemini API Key
st.subheader("1. AI Configuration")
api_key = st.text_input("Enter Gemini API Key", type="password", help="Required for extracting data from documents.")
if api_key:
    st.session_state['gemini_api_key'] = api_key
    st.success("API Key saved for this session.")

st.markdown("---")

# Section 2: Permanent Rules Storage
st.subheader("2. Rules, Statutes & Circulars")
st.markdown("*Upload documents here to be saved permanently for all future calculations.*")

uploaded_rule = st.file_uploader("Upload New Regulation (PDF)", type=['pdf'])
if uploaded_rule:
    if st.button("Save Rule Permanently"):
        path = utils.save_permanent_rule(uploaded_rule)
        st.success(f"Saved: {uploaded_rule.name}")

# Display currently saved rules
st.write("### 📂 Currently Saved Rules:")
saved_files = utils.list_saved_rules()
if saved_files:
    for f in saved_files:
        st.text(f"• {f}")
else:
    st.warning("No permanent rules saved yet.")
