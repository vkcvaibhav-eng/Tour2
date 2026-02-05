import streamlit as st

st.set_page_config(page_title="TA/DA Automation", layout="wide")

st.title("🏛️ TA/DA Reimbursement Automation")
st.markdown("""
This application automates the creation of TA/DA claims using AI.

**Workflow:**
1. **Settings & Rules:** Set your API Key and upload permanent regulations (Statutes/Circulars).
2. **Upload & Extract:** Upload current trip documents (Salary slip, Tour Diary, Tickets).
3. **Review & Calculate:** Edit extracted data and view the calculation matrix.
4. **Export:** Download the final sheet in MS Word (A3 Size).
""")

st.info("Navigate using the sidebar menu to begin.")