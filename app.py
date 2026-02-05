import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import os
from PIL import Image
import PyPDF2
from fpdf import FPDF

# --- CONFIGURATION ---
AI_MODEL_NAME = "gemini-3-flash-preview" 

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

# --- DATA PERSISTENCE ---
def save_data():
    """Saves the current state of data to a JSON file"""
    data = {
        "tour": st.session_state.tour_data.to_dict(orient="records"),
        "stay": st.session_state.stay_data.to_dict(orient="records"),
        "salary": st.session_state.salary_info
    }
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f)
    st.toast("✅ Data Saved Successfully!")

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

# --- SIDEBAR DASHBOARD ---
with st.sidebar:
    st.header("🏢 NAU Admin Panel")
    api_key = st.text_input("🔑 Gemini API Key", type="password")
    
    st.divider()
    st.subheader("👤 User Profile")
    st.session_state.salary_info["Designation"] = st.text_input("Designation", value=st.session_state.salary_info.get("Designation", ""))
    st.session_state.salary_info["Basic Pay"] = st.number_input("Basic Pay", value=st.session_state.salary_info.get("Basic Pay", 0))
    
    st.divider()
    if st.button("🗑️ Clear All Data", type="secondary"):
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        st.rerun()

# --- MAIN PAGE ---
st.title("🚜 NAU TA/DA Assistant")
# Removed Calculation & Report Tab
tabs = st.tabs(["📤 Step 1: Upload Proofs", "✏️ Step 2: Edit & Save Data"])

# --- TAB 1: UPLOAD PROOFS ---
with tabs[0]:
    st.header("Upload Documents")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Tickets/Fuel")
        st.file_uploader("Upload Travel Tickets", type=["png", "jpg", "pdf"], key="ticket_up")
    with col2:
        st.subheader("Stay/Hotel")
        st.file_uploader("Upload Hotel Bills", type=["png", "jpg", "pdf"], key="stay_up")
    
    if st.button("🚀 Extract Data"):
        st.info("AI Extraction logic would process files here...")

# --- TAB 2: EDIT & SAVE (Modified as requested) ---
with tabs[1]:
    st.header("📝 Verify and Finalize Data")
    st.write("Correct any information below. Changes are saved locally when you click 'Save'.")
    
    st.subheader("1. Travel Details")
    # Data editor updates local variable
    edited_tour = st.data_editor(
        st.session_state.tour_data,
        num_rows="dynamic",
        use_container_width=True,
        key="tour_editor"
    )
    
    st.divider()
    
    st.subheader("2. Accommodation Details")
    edited_stay = st.data_editor(
        st.session_state.stay_data,
        num_rows="dynamic",
        use_container_width=True,
        key="stay_editor"
    )

    # NO EXPORT BUTTON HERE - Just Save
    if st.button("💾 Save All Data"):
        # Update session state with the edited data
        st.session_state.tour_data = edited_tour
        st.session_state.stay_data = edited_stay
        # Save to JSON file
        save_data()

    # Optional: Direct PDF Download button here if you still want a report 
    # but without a dedicated tab
    if not st.session_state.tour_data.empty:
        st.divider()
        if st.button("📄 Quick Download PDF Report"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="NAU TA/DA Claim", ln=1, align='C')
            pdf.output("TA_Claim.pdf")
            st.success("PDF generated from saved data!")

