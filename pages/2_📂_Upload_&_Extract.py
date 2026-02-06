import streamlit as st
import utils
import time
import os

st.set_page_config(page_title="Upload & Extract", layout="wide")

st.title("📂 Upload & Extract Data")

if 'gemini_api_key' not in st.session_state:
    st.error("Please set your Gemini API Key in the Settings page first.")
    st.stop()

# --- 1. SETUP SESSION STORAGE ---
# Create a folder to save files for this session
UPLOAD_DIR = "session_uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Initialize Session State list for files
if 'session_file_paths' not in st.session_state:
    st.session_state['session_file_paths'] = []

# --- 2. UPLOAD INTERFACE ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Personal Documents")
    salary_slip = st.file_uploader("Salary Slip", type=['pdf', 'jpg', 'png'], key="uploader_salary")
    tour_diary = st.file_uploader("Tour Diary", type=['pdf', 'jpg', 'png'], key="uploader_diary")

with col2:
    st.subheader("Expense Documents")
    tickets = st.file_uploader("Tickets / Fare Enquiry", accept_multiple_files=True, key="uploader_tickets")

st.markdown("---")

# --- 3. LOGIC: SAVE FILES TO DISK (FOR SESSION) ---
def save_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

# Check and Save Salary Slip
if salary_slip:
    path = save_uploaded_file(salary_slip)
    if path and path not in st.session_state['session_file_paths']:
        st.session_state['session_file_paths'].append(path)

# Check and Save Tour Diary
if tour_diary:
    path = save_uploaded_file(tour_diary)
    if path and path not in st.session_state['session_file_paths']:
        st.session_state['session_file_paths'].append(path)

# Check and Save Tickets
if tickets:
    for t in tickets:
        path = save_uploaded_file(t)
        if path and path not in st.session_state['session_file_paths']:
            st.session_state['session_file_paths'].append(path)

# --- 4. DISPLAY SAVED FILES ---
if st.session_state['session_file_paths']:
    st.success(f"✅ {len(st.session_state['session_file_paths'])} Documents Saved for this Session:")
    for p in st.session_state['session_file_paths']:
        st.caption(f"📄 {os.path.basename(p)}")
else:
    st.info("ℹ️ Upload files above. They will be saved for the session.")

st.markdown("---")

# --- 5. ANALYZE BUTTON ---
if st.button("🚀 Analyze & Extract Data"):
    # Check if we have files in session (not just in the uploader widget)
    if not st.session_state['session_file_paths']:
        st.warning("⚠️ No files saved! Please upload Salary Slip and Tour Diary.")
    else:
        with st.spinner("AI is reading your saved documents..."):
            
            # Send the SAVED PATHS to utils (instead of file objects)
            extracted_data = utils.call_gemini_extraction(
                st.session_state['gemini_api_key'], 
                st.session_state['session_file_paths'], # Sending Paths now
                "Extract TA DA details"
            )
            
            # Save Result
            st.session_state['extracted_data'] = extracted_data
            
            st.success("Extraction Complete! Moving to Tour Diary...")
            
            time.sleep(1)
            try:
                st.switch_page("pages/3_🗓️_Tour_Diary.py") 
            except:
                st.warning("Could not auto-switch. Please click '3_🗓️_Tour_Diary' in the sidebar.")
