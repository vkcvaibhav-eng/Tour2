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

# --- HELPER FUNCTIONS ---

def get_gemini_response(prompt, content_parts, api_key):
    """Sends text/images to Gemini Flash"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(AI_MODEL_NAME) 
        response = model.generate_content([prompt, *content_parts])
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

def extract_text_from_pdf(uploaded_file):
    reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def save_data():
    """Persist data to local JSON"""
    data = {
        "tour": st.session_state.tour_data.to_dict(orient="records"),
        "stay": st.session_state.stay_data.to_dict(orient="records"),
        "salary": st.session_state.salary_info
    }
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f)
    st.toast("Changes Saved Successfully!")

def load_data():
    """Load data from local JSON"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
            st.session_state.tour_data = pd.DataFrame(data.get("tour", []))
            st.session_state.stay_data = pd.DataFrame(data.get("stay", []))
            st.session_state.salary_info = data.get("salary", {})

if "loaded" not in st.session_state:
    load_data()
    st.session_state.loaded = True

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    st.divider()
    st.subheader("📜 Rules & Statutes")
    uploaded_rules = st.file_uploader("Upload Rule PDFs", type=["pdf"], accept_multiple_files=True)
    if uploaded_rules:
        for rule_file in uploaded_rules:
            with open(os.path.join(ST_RULES_DIR, rule_file.name), "wb") as f:
                f.write(rule_file.getbuffer())
        st.success("Rules updated!")

# --- MAIN APP ---
st.title("🚜 NAU TA/DA Reimbursement Assistant")
tabs = st.tabs(["1. Upload Proofs", "2. Edit Data (Tour/Stay)", "3. Calculation & Report"])

# --- TAB 1: UPLOADS ---
with tabs[0]:
    st.header("Step 1: Upload Documents")
    # [Extraction logic for salary and tickets remains as per original implementation]
    st.info("Upload your salary slip and travel tickets here for AI extraction.")

# --- TAB 2: DATA ENTRY (MODIFIED) ---
with tabs[1]:
    st.header("📝 Verify & Edit Details")
    st.info("💡 IMPORTANT: For 'Private Vehicle', enter 'Enquiry Fare' in the right column.")
    
    # Editor for Tour Data
    edited_tour = st.data_editor(
        st.session_state.tour_data,
        num_rows="dynamic",
        use_container_width=True,
        key="tour_editor"
    )
    
    st.divider()
    st.subheader("B. Stay Details")
    # Editor for Stay Data
    edited_stay = st.data_editor(
        st.session_state.stay_data,
        num_rows="dynamic",
        use_container_width=True,
        key="stay_editor"
    )

    # UPDATED: Button to sync edited data to session state for the next page
    if st.button("✅ Save & Send to Calculation"):
        st.session_state.tour_data = edited_tour
        st.session_state.stay_data = edited_stay
        save_data()
        st.success("Data synchronized! Proceed to Tab 3 for the report.")

# --- TAB 3: CALCULATION & REPORT ---
with tabs[2]:
    st.header("🧮 Calculation & Report")
    
    # Check if we have data to calculate
    if st.session_state.tour_data.empty:
        st.warning("No data found. Please edit and save data in Tab 2 first.")
    else:
        st.subheader("Final Claim Summary")
        # Display the current data being used for calculations
        st.write("Current Verified Data:")
        st.dataframe(st.session_state.tour_data)
        
        # [PDF generation logic using st.session_state.tour_data as updated in Tab 2]
        if st.button("Generate Final PDF"):
            # Your existing PDF logic here...
            st.success("PDF generated using the edited data.")
