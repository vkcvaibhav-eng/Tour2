import streamlit as st
import utils
import os

st.set_page_config(page_title="Settings", layout="wide")
st.title("⚙️ Settings & Rules")

# ==========================================
# SECTION 1: API CONFIGURATION (Restored)
# ==========================================
st.subheader("1. AI Configuration")
api_key = st.text_input(
    "Enter Gemini API Key", 
    type="password", 
    help="Required for extracting data from documents.",
    value=st.session_state.get('gemini_api_key', '')
)

if api_key:
    st.session_state['gemini_api_key'] = api_key
    st.success("✅ API Key is active for this session.")

st.markdown("---")

# ==========================================
# SECTION 2: PERMANENT RULES (Fixed Error)
# ==========================================
st.subheader("2. Rules, Statutes & Circulars")
st.markdown("*Upload documents here to be saved permanently for all future calculations.*")

# accept_multiple_files=True means this returns a LIST of files
uploaded_rules = st.file_uploader("Upload New Regulation (PDF)", type=['pdf'], accept_multiple_files=True)

if uploaded_rules:
    if st.button("Save Rules Permanently"):
        # We loop through the list to save them one by one
        for rule_file in uploaded_rules:
            path = utils.save_permanent_rule(rule_file)
            if path:
                st.success(f"Saved: {rule_file.name}")
        
        # Refresh the list to show the new files immediately
        st.rerun()

# Display currently saved rules
st.write("### 📂 Currently Saved Rules:")
saved_files = utils.list_saved_rules()

if saved_files:
    for f in saved_files:
        st.text(f"• {f}")
else:
    st.warning("No permanent rules saved yet.")
