import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import os
from PIL import Image
import PyPDF2
from fpdf import FPDF

# --- CONFIGURATION ---
# You can change the model name here if a newer version (like 3.0) becomes available.
# currently 'gemini-2.0-flash' is the latest high-speed model.
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

def get_gemini_response(prompt, content_parts, api_key):
    """Sends text/images to Gemini Flash"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(AI_MODEL_NAME) 
        # Streamlit spinner usually handles the UI waiting
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

def load_rules_context():
    """Reads all uploaded rule PDFs to create a context string"""
    rules_text = ""
    files = os.listdir(ST_RULES_DIR)
    for f in files:
        path = os.path.join(ST_RULES_DIR, f)
        try:
            reader = PyPDF2.PdfReader(path)
            for page in reader.pages:
                rules_text += page.extract_text() + "\n"
        except:
            pass
    return rules_text

def save_data():
    """Persist data to local JSON"""
    data = {
        "tour": st.session_state.tour_data.to_dict(orient="records"),
        "stay": st.session_state.stay_data.to_dict(orient="records"),
        "salary": st.session_state.salary_info
    }
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f)
    st.toast("Data Saved Successfully!")

def load_data():
    """Load data from local JSON"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
            st.session_state.tour_data = pd.DataFrame(data.get("tour", []))
            st.session_state.stay_data = pd.DataFrame(data.get("stay", []))
            st.session_state.salary_info = data.get("salary", {})

# Load saved data on startup
if "loaded" not in st.session_state:
    load_data()
    st.session_state.loaded = True

# --- SIDEBAR: SETTINGS & RULES ---
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    
    st.divider()
    st.subheader("📜 Rules & Statutes")
    st.info("Upload Circulars/Statutes here. The AI will read these for calculations.")
    uploaded_rules = st.file_uploader("Upload Rule PDFs", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_rules:
        for rule_file in uploaded_rules:
            with open(os.path.join(ST_RULES_DIR, rule_file.name), "wb") as f:
                f.write(rule_file.getbuffer())
        st.success("Rules updated!")
    
    # List current rules
    st.write("Current Rule Files:")
    for f in os.listdir(ST_RULES_DIR):
        col1, col2 = st.columns([0.8, 0.2])
        col1.caption(f)
        if col2.button("X", key=f):
            os.remove(os.path.join(ST_RULES_DIR, f))
            st.rerun()

# --- MAIN APP ---
st.title("🚜 NAU TA/DA Reimbursement Assistant")
st.markdown(f"**Engine:** {AI_MODEL_NAME} | Automated Tool for Navsari Agricultural University")

tabs = st.tabs(["1. Upload Proofs", "2. Edit Data (Tour/Stay)", "3. Calculation & Report"])

# --- TAB 1: UPLOADS & EXTRACTION ---
with tabs[0]:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Step 1: Salary Slip")
        salary_file = st.file_uploader("Upload Salary Slip (PDF/Img)", type=["pdf", "jpg", "png"])
        
        if salary_file and st.button("Extract Salary Info"):
            if not api_key:
                st.error("Please enter API Key in sidebar")
            else:
                with st.spinner("Analyzing Salary Slip..."):
                    content = []
                    if salary_file.type == "application/pdf":
                        content.append(extract_text_from_pdf(salary_file))
                    else:
                        content.append(Image.open(salary_file))
                    
                    prompt = """
                    Extract the following from this salary slip in JSON format:
                    {"Basic Pay": number, "Pay Level": "string", "Designation": "string"}
                    """
                    res = get_gemini_response(prompt, content, api_key)
                    try:
                        clean_json = res.replace("```json", "").replace("```", "")
                        st.session_state.salary_info = json.loads(clean_json)
                        st.success("Salary Info Extracted!")
                        save_data()
                    except:
                        st.error("Could not parse AI response. Please enter manually.")

        st.text_input("Designation", value=st.session_state.salary_info.get("Designation", ""))
        st.text_input("Pay Level", value=st.session_state.salary_info.get("Pay Level", ""))
        st.number_input("Basic Pay", value=st.session_state.salary_info.get("Basic Pay", 0))

    with col2:
        st.subheader("Step 2: Tour Diary & Tickets")
        tour_files = st.file_uploader("Upload Tour Diary, Tickets, Enquiry Fares", accept_multiple_files=True)
        
        if tour_files and st.button("Auto-Fill Tour Data"):
            if not api_key:
                st.error("Need API Key")
            else:
                with st.spinner("Reading Tour Diary & Tickets..."):
                    combined_content = ["Context: Extract a chronological list of travel legs."]
                    for tf in tour_files:
                        if tf.type == "application/pdf":
                            combined_content.append(f"File {tf.name}: " + extract_text_from_pdf(tf))
                        else:
                            combined_content.append(Image.open(tf))
                    
                    # Specific prompt for Private Vehicle / Enquiry logic
                    prompt = """
                    Based on the uploaded tour diary and tickets, create a JSON list of trips.
                    Format: [{"Date": "DD-MM-YYYY", "From": "City", "To": "City", "Mode": "Bus/Rail/Private/Air", "Distance_KM": number, "Ticket_Amount": number, "Enquiry_Fare_If_Private": number, "Remark": "string"}]
                    
                    CRITICAL RULES:
                    1. If the mode is "Private Vehicle" or similar:
                       - Set "Ticket_Amount" to 0.
                       - Look for any document labeled "Enquiry Fare" or "GSRT Fare" for that route and put that amount in "Enquiry_Fare_If_Private".
                    2. If the mode is "Bus", "Rail", or "Air":
                       - Put the fare in "Ticket_Amount".
                    """
                    
                    res = get_gemini_response(prompt, combined_content, api_key)
                    try:
                        clean_json = res.replace("```json", "").replace("```", "")
                        new_data = pd.DataFrame(json.loads(clean_json))
                        # Ensure columns exist
                        required_cols = ["Date", "From", "To", "Mode", "Ticket_Amount", "Enquiry_Fare_If_Private"]
                        for col in required_cols:
                            if col not in new_data.columns:
                                new_data[col] = ""
                                
                        st.session_state.tour_data = new_data
                        save_data()
                        st.success("Tour Data Extracted!")
                    except Exception as e:
                        st.error(f"AI parsing error: {e}")

# --- TAB 2: DATA ENTRY ---
with tabs[1]:
    st.header("📝 Verify & Edit Details")
    
    st.subheader("A. Tour Details")
    st.info("💡 IMPORTANT: For 'Private Vehicle', you must enter the 'Enquiry Fare' (the cost if you had taken a bus/train) in the column on the right.")
    
    edited_tour = st.data_editor(
        st.session_state.tour_data, 
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Enquiry_Fare_If_Private": st.column_config.NumberColumn(
                "Enquiry Fare (Private Vehicle)",
                help="If using private car, enter the government bus/train fare here."
            ),
            "Ticket_Amount": st.column_config.NumberColumn(
                "Actual Ticket Paid",
                help="Amount paid for Bus/Train/Flight ticket."
            )
        }
    )
    st.session_state.tour_data = edited_tour
    
    st.divider()
    
    st.subheader("B. Accommodation / Stay Details")
    st.caption("Enter hotel or guest house details.")
    edited_stay = st.data_editor(st.session_state.stay_data, num_rows="dynamic", use_container_width=True)
    st.session_state.stay_data = edited_stay
    
    if st.button("Save Changes"):
        save_data()

# --- TAB 3: CALCULATION & REPORT ---
with tabs[2]:
    st.header("💰 Calculation & Final Report")
    
    if st.button("Run Compliance Check & Calculate"):
        if not api_key:
            st.error("Need API Key for Rule Checking")
        else:
            with st.spinner(f"Consulting Statutes with {AI_MODEL_NAME}..."):
                # 1. Load Rules
                rules_context = load_rules_context()
                
                # 2. Prepare Data Context
                data_context = f"""
                Salary Info: {st.session_state.salary_info}
                Tour Data: {st.session_state.tour_data.to_json(orient='records')}
                Stay Data: {st.session_state.stay_data.to_json(orient='records')}
                """
                
                # 3. Ask Gemini to Calculate based on Rules
                prompt = f"""
                You are an accountant for Navsari Agricultural University.
                Using the attached Rules/Statutes (Context) and the User Data provided:
                
                1. **Travel Allowance (TA) Calculation**:
                   - Check the 'Mode'. 
                   - IF Mode is "Private Vehicle": The reimbursable amount is the 'Enquiry_Fare_If_Private' value. (As per university rule: Private vehicle mileage is not given, only equivalent fare).
                   - IF Mode is Public Transport (Bus/Rail): The reimbursable amount is the 'Ticket_Amount'.
                   
                2. **Daily Allowance (DA) Calculation**:
                   - Determine the DA rate based on the user's 'Pay Level' (from Salary Info) and the 'City' classification (X, Y, Z or similar) found in the Rules.
                   - Calculate total DA based on the duration of the tour (Dates).
                
                3. **Stay/Lodging Calculation**:
                   - Check the 'Bill_Amount'. Compare it against the maximum limit allowed for their Pay Level in the Rules.
                
                Output a detailed summary in Markdown.
                Finally, provide a "GRAND TOTAL CLAIM" amount.
                
                USER DATA:
                {data_context}
                
                RULES CONTEXT (Statutes/Circulars):
                {rules_context[:50000]} 
                """
                
                report = get_gemini_response(prompt, [], api_key)
                st.markdown(report)
    
    st.divider()
    
    st.subheader("Export Final PDF")
    
    if st.button("Download PDF Report"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        pdf.cell(200, 10, txt="NAU TA/DA Reimbursement Claim", ln=1, align='C')
        pdf.ln(10)
        
        pdf.set_font("Arial", size=10)
        designation = st.session_state.salary_info.get('Designation', 'Associate Professor')
        pdf.cell(200, 10, txt=f"Name/Designation: {designation}", ln=1)
        
        pdf.ln(5)
        pdf.cell(200, 10, txt="--- Tour Summary ---", ln=1)
        
        # Simple Table in PDF
        col_width = 30
        headers = ["Date", "From", "To", "Mode", "Claim Amt"]
        for head in headers:
            pdf.cell(col_width, 10, head, border=1)
        pdf.ln()
        
        for index, row in st.session_state.tour_data.iterrows():
            date = str(row.get("Date", ""))[:10]
            frm = str(row.get("From", ""))[:10]
            to = str(row.get("To", ""))[:10]
            mode = str(row.get("Mode", ""))[:10]
            
            # Logic for Fare printing in PDF
            amt = row.get("Ticket_Amount", 0)
            if "private" in str(row.get("Mode", "")).lower():
                amt = row.get('Enquiry_Fare_If_Private', 0)
            
            pdf.cell(col_width, 10, date, border=1)
            pdf.cell(col_width, 10, frm, border=1)
            pdf.cell(col_width, 10, to, border=1)
            pdf.cell(col_width, 10, mode, border=1)
            pdf.cell(col_width, 10, str(amt), border=1)
            pdf.ln()
            
        pdf.ln(10)
        pdf.cell(200, 10, txt="Note: Original tickets/enquiry proofs attached separately.", ln=1)
        
        # Output
        pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore') 
        
        st.download_button(
            label="Download Final Claim PDF",
            data=pdf_bytes,
            file_name="NAU_TA_DA_Claim.pdf",
            mime="application/pdf"
        )
