import streamlit as st
import utils
import time # Added for the pause before switching

st.set_page_config(page_title="Upload & Extract", layout="wide") # Good practice

st.title("📂 Upload & Extract Data")

if 'gemini_api_key' not in st.session_state:
    st.error("Please set your Gemini API Key in the Settings page first.")
    st.stop()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Personal Documents")
    salary_slip = st.file_uploader("Salary Slip", type=['pdf', 'jpg', 'png'])
    tour_diary = st.file_uploader("Tour Diary", type=['pdf', 'jpg', 'png'])

with col2:
    st.subheader("Expense Documents")
    tickets = st.file_uploader("Tickets / Fare Enquiry", accept_multiple_files=True)
    hotel_bills = st.file_uploader("Hotel / Guest House Bills", accept_multiple_files=True)

st.markdown("---")

# --- UPDATED BUTTON LOGIC ---
if st.button("🚀 Analyze & Extract Data"):
    if not salary_slip or not tour_diary:
        st.warning("⚠️ Please upload at least the Salary Slip and Tour Diary.")
    else:
        with st.spinner("AI is reading your documents..."):
            # 1. Call the AI function from utils.py
            extracted_data = utils.call_gemini_extraction(
                st.session_state['gemini_api_key'], 
                [salary_slip, tour_diary], 
                "Extract TA DA details"
            )
            
            # 2. SAVE to Session State (This "sends" it to Page 3)
            st.session_state['extracted_data'] = extracted_data
            
            # 3. Success Message
            st.success("Extraction Complete! Moving to Tour Diary...")
            
            # 4. Auto-Switch to Page 3
            time.sleep(1) # Small pause so user sees the success message
            try:
                # IMPORTANT: Ensure the filename inside the quotes MATCHES your actual file exactly
                st.switch_page("pages/3_🗓️_Tour_Diary.py") 
            except:
                st.warning("Could not auto-switch. Please click '3_🗓️_Tour_Diary' in the sidebar.")
                # Fallback if file structure is different:
                # st.switch_page("3_🗓️_Tour_Diary.py")
