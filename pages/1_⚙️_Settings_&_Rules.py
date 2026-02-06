import streamlit as st
import utils
import os
import importlib 

# --- FIX: Force reload utils to recognize new functions ---
importlib.reload(utils) 
# ----------------------------------------------------------

st.title("⚙️ Settings & Rules")

# ==========================================
# SECTION 1: API CONFIGURATION
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
# SECTION 2: PERMANENT RULES
# ==========================================
st.subheader("2. Rules, Statutes & Circulars")
st.markdown("*Upload documents here to be saved permanently for all future calculations.*")

# This handles both Single File AND Multiple Files to prevent errors
uploaded_files = st.file_uploader(
    "Upload New Regulation (PDF)", 
    type=['pdf'], 
    accept_multiple_files=True # Safer to allow multiple, we handle it below
)

if uploaded_files:
    if st.button("Save Rule Permanently"):
        # We loop through the list to save them one by one
        for rule_file in uploaded_files:
            # Check if utils actually has the function (Double Safety)
            if hasattr(utils, 'save_permanent_rule'):
                path = utils.save_permanent_rule(rule_file)
                if path:
                    st.success(f"Saved: {rule_file.name}")
            else:
                st.error("Error: utils.py is not updated. Please reboot the app.")
        
        # Refresh to show new files
        st.rerun()

# Display currently saved rules
st.write("### 📂 Currently Saved Rules:")
saved_files = utils.list_saved_rules()

if saved_files:
    for f in saved_files:
        st.text(f"• {f}")
else:
    st.warning("No permanent rules saved yet.")
