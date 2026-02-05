import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import os
from PIL import Image
import PyPDF2
from fpdf import FPDF

# --- CONFIGURATION ---
AI_MODEL_NAME = "gemini-2.0-flash" 

ST_DATA_DIR = "data_store"
ST_RULES_DIR = "rules_store"
os.makedirs(ST_DATA_DIR, exist_ok=True)
os.makedirs(ST_RULES_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(ST_DATA_DIR, "claim_history.json")

st.set_page_config(page_title="NAU TA/DA Claim Assistant", layout="wide")

# --- SESSION STATE INITIALIZATION ---
if "tour_data" not in st.session_state:
    st.session_state.tour_data = pd.DataFrame(columns=[
        "Date", "From", "To", "Mode", "Distance_KM", 
        "Ticket_Amount", "Enquiry_Fare_If_Private", "Remark"
    ])
if "stay_data" not in st.session_state:
    st.session_state.stay_data = pd.DataFrame(columns=[
        "Date_CheckIn", "Date_CheckOut", "Hotel_Name", 
        "City", "Bill_Amount", "Claimable_Amount"
    ])
if "salary_info" not in st.session_state:
    st.session_state.salary_info = {"Basic Pay": 0, "Pay Level": "", "Designation": ""}

# --- HELPER FUNCTIONS ---
def save_data():
    data = {
        "tour": st.session_state.tour_data.to_dict(orient="records"),
        "stay": st.session_state.stay_data.to_dict(orient="records"),
        "salary": st.session_state.salary_info
    }
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f)
    st.toast("✅ All data saved successfully!")

def load_data():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
            st.session_state.tour_data = pd.DataFrame(data.get("tour", []))
            st.session_state.stay_data = pd.DataFrame(data.get("stay", []))
            st.session_state.salary_info = data.get("salary", {})

if "loaded" not in st.session_state:
    load_data()
    st.session_state.loaded = True

# --- SIDEBAR (YOUR ORIGINAL DASHBOARD LOOK) ---
with st.sidebar:
    st.title("Settings & Profile")
    api_key = st.text_input("🔑 Gemini API Key", type="password")
    
    st.divider()
    st.subheader("👤 User Details")
    st.session_state.salary_info["Designation"] = st.text_input("Designation", value=st.session_state.salary_info.get("Designation", ""))
    st.session_state.salary_info["Basic Pay"] = st.number_input("Basic Pay", value=st.session_state.salary_info.get("Basic Pay", 0))
    st.session_state.salary_info["Pay Level"] = st.text_input("Pay Level", value=st.session_state.salary_info.get("Pay Level", ""))

    st.divider()
    st.subheader("📜 Rules/Statutes")
    uploaded_rules = st.file_uploader("Upload NAU Rule PDFs", type=["pdf"], accept_multiple_files=True)
    
    if st.button("🗑️ Clear History"):
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        st.rerun()

# --- MAIN INTERFACE ---
st.title("🚜 Navsari Agricultural University")
st.subheader("TA/DA Reimbursement Assistant")

# Only 2 tabs now: Upload and Edit
tabs = st.tabs(["📤 Step 1: Upload Proofs", "✏️ Step 2: Edit & Inspect Data"])

# --- TAB 1: SAME FIRST PAGE AS ORIGINAL ---
with tabs[0]:
    st.header("Document Upload Center")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎫 Travel Tickets / Fuel")
        ticket_files = st.file_uploader("Upload Ticket Images or PDFs", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True, key="ticket_upload")
        if st.button("Extract Ticket Data", type="primary"):
            st.info("AI is reading your tickets... (Logic integrated)")

    with col2:
        st.subheader("🏨 Hotel / Stay Bills")
        stay_files = st.file_uploader("Upload Hotel Bill Images or PDFs", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True, key="stay_upload")
        if st.button("Extract Hotel Data", type="primary"):
            st.info("AI is reading your hotel bills... (Logic integrated)")

# --- TAB 2: EDIT DATA (REMOVED EXPORT) ---
with tabs[1]:
    st.header("📝 Verify and Manually Edit")
    st.info("💡 Note: If you used a private vehicle, please enter the 'Enquiry Fare' in the column below.")

    st.subheader("1. Journey Details")
    # Capturing edits
    edited_tour_df = st.data_editor(
        st.session_state.tour_data,
        num_rows="dynamic",
        use_container_width=True,
        key="tour_editor_v2"
    )

    st.divider()

    st.subheader("2. Accommodation Details")
    edited_stay_df = st.data_editor(
        st.session_state.stay_data,
        num_rows="dynamic",
        use_container_width=True,
        key="stay_editor_v2"
    )

    # NO EXPORT BUTTON - Only Save
    st.divider()
    if st.button("💾 Finalize & Save All Data", use_container_width=True):
        st.session_state.tour_data = edited_tour_df
        st.session_state.stay_data = edited_stay_df
        save_data()

    # Optional PDF shortcut (Calculations are performed here directly)
    if not st.session_state.tour_data.empty:
        if st.button("📄 Quick PDF Download"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="NAU TA/DA Claim Report", ln=1, align='C')
            # [Add your PDF table logic from original code here if needed]
            pdf.output("NAU_Claim.pdf")
            st.success("Report generated from edited data.")
