import streamlit as st

st.set_page_config(page_title="TA/DA Automation", layout="wide")

st.title("🏛️ TA/DA Reimbursement Automation")

# --- API KEY SECTION (Moved to Home) ---
st.subheader("1. AI Configuration")
st.markdown("Enter your Gemini API Key here. It will be saved for this session.")

api_key = st.text_input(
    "Gemini API Key", 
    type="password", 
    help="Required for extracting data from documents.",
    value=st.session_state.get('gemini_api_key', '')
)

if api_key:
    st.session_state['gemini_api_key'] = api_key
    st.success("✅ API Key is active for this session.")
else:
    st.warning("⚠️ Please enter your API Key to proceed.")

st.markdown("---")

st.markdown("""
### **Workflow:**
1. **Tour Diary:** Upload your scanned Tour Diary. The AI will extract dates, times, and places. You can edit the result.
2. **TA Calculation:** Upload your Tickets and University TA Rules. The system will calculate mileage and fares.
3. **DA Calculation:** Upload DA Circulars/Rules. The system will calculate your Daily Allowance.
4. **Export:** Download the final claim form in Word format.
""")

st.info("Please navigate to **'1. Tour Diary'** from the sidebar to start.")
