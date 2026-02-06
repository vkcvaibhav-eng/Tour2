import streamlit as st
import utils 

st.title("⚙️ Settings & Rules")

# ... existing API key code ...

st.subheader("Manage Rules & Statutes")
# Note: accept_multiple_files=True returns a LIST
uploaded_rules = st.file_uploader("Upload PDF Rules", type="pdf", accept_multiple_files=True)

if uploaded_rules:
    for rule_file in uploaded_rules:
        # We loop through the list and save one by one
        path = utils.save_permanent_rule(rule_file)
        if path:
            st.success(f"Saved: {rule_file.name}")
