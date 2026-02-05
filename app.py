import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import os
from PIL import Image
import PyPDF2
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURATION ---
AI_MODEL_NAME = "gemini-3-pro-preview" 
ST_DATA_DIR = "data_store"
ST_RULES_DIR = "rules_store"
os.makedirs(ST_DATA_DIR, exist_ok=True)
os.makedirs(ST_RULES_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(ST_DATA_DIR, "nau_claim_history.json")

st.set_page_config(page_title="NAU TA/DA Assistant", layout="wide", page_icon="🚜")

# --- CSS FOR VISIBILITY ---
st.markdown("""
<style>
    .stTextArea textarea {font-size: 14px;}
    .reportview-container .main .block-container {max_width: 95%;}
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
def init_session():
    # 1. Salary Info
    if "salary_info" not in st.session_state:
        st.session_state.salary_info = {"Basic Pay": 0, "Pay Level": "Level 12", "Designation": ""}
    
    # 2. Tour Diary (The Master Chronological Record)
    # Matches the "Tour Diary" PDF columns
    if "diary_entries" not in st.session_state:
        st.session_state.diary_entries = pd.DataFrame(columns=[
            "Dep_Date", "Dep_Time", "Dep_Place",
            "Arr_Date", "Arr_Time", "Arr_Place",
            "Mode", "Class", "Ticket_Amount",
            "Enquiry_Fare_If_Private", # Crucial for private vehicle
            "Vehicle_Details", # For road travel details
            "Stay_Duration_Hrs", # Helper for DA
            "Remark"
        ])
    
    # 3. Calculation States (TA & DA Separated and Editable)
    if "ta_calc_table" not in st.session_state:
        st.session_state.ta_calc_table = pd.DataFrame(columns=[
            "Route", "Mode_Used", "Claimed_Fare", "Admissible_Fare", "Rule_Applied", "Justification"
        ])
    if "da_calc_table" not in st.session_state:
        st.session_state.da_calc_table = pd.DataFrame(columns=[
            "Date", "City", "City_Class", "DA_Rate", "Days_Claimable", "Total_DA", "Rule_Applied"
        ])

init_session()

# --- HELPER FUNCTIONS ---

def get_gemini_response(prompt, content_parts, api_key, response_format="text"):
    try:
        if not api_key:
            return "Error: API Key Missing"
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(AI_MODEL_NAME)
        
        # Generation config
        config = genai.types.GenerationConfig(
            candidate_count=1,
            temperature=0.2,
        )
        
        if response_format == "json":
             config.response_mime_type = "application/json"

        response = model.generate_content([prompt, *content_parts], generation_config=config)
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

# --- SIDEBAR ---
with st.sidebar:
    st.title("🚜 NAU Assistant")
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    st.subheader("📜 Rules/Statutes")
    uploaded_rules = st.file_uploader("Upload Circulars", type=["pdf"], accept_multiple_files=True)
    if uploaded_rules:
        for rule_file in uploaded_rules:
            with open(os.path.join(ST_RULES_DIR, rule_file.name), "wb") as f:
                f.write(rule_file.getbuffer())
        st.success("Rules Loaded!")

# --- MAIN APP ---
st.title("NAU TA/DA Reimbursement Assistant")

tabs = st.tabs(["1. Uploads & Salary", "2. Tour Diary (Master Data)", "3. Calculation (TA & DA) & Report"])

# --- TAB 1: UPLOADS ---
with tabs[0]:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("A. Salary Details")
        st.caption("Needed for Pay Level & DA Rate logic")
        sal_file = st.file_uploader("Upload Salary Slip", type=["pdf", "jpg", "png"])
        if sal_file and st.button("Extract Salary Info"):
            with st.spinner("Reading Salary Slip..."):
                content = []
                if sal_file.type == "application/pdf":
                    content.append(extract_text_from_pdf(sal_file))
                else:
                    content.append(Image.open(sal_file))
                
                prompt = """Extract JSON: {"Basic Pay": number, "Pay Level": "string", "Designation": "string"}"""
                res = get_gemini_response(prompt, content, api_key, "json")
                try:
                    st.session_state.salary_info = json.loads(res)
                    st.success("Extracted!")
                except:
                    st.error("Manual entry required.")

        # Editable Salary Fields
        c1, c2, c3 = st.columns(3)
        st.session_state.salary_info["Designation"] = c1.text_input("Designation", st.session_state.salary_info.get("Designation"))
        st.session_state.salary_info["Pay Level"] = c2.text_input("Pay Level", st.session_state.salary_info.get("Pay Level"))
        st.session_state.salary_info["Basic Pay"] = c3.number_input("Basic Pay", value=float(st.session_state.salary_info.get("Basic Pay", 0)))

    with col2:
        st.subheader("B. Tour Proofs")
        st.caption("Tickets, Tour Diary, Enquiry Fares (for Private Vehicle)")
        tour_files = st.file_uploader("Upload Documents", accept_multiple_files=True)
        
        if tour_files and st.button("Extract to Tour Diary"):
            if not api_key:
                st.error("API Key required")
            else:
                with st.spinner("AI is converting proofs to Chronological Diary..."):
                    content = ["You are a Data Entry Clerk. Create a chronological list of journey legs."]
                    for tf in tour_files:
                        if tf.type == "application/pdf":
                            content.append(f"File {tf.name}: " + extract_text_from_pdf(tf))
                        else:
                            content.append(Image.open(tf))
                    
                    prompt = """
                    Analyze the documents and output a JSON list of objects representing the Tour Diary rows.
                    Follow this EXACT format for keys:
                    [
                        {
                            "Dep_Date": "DD-MM-YYYY", "Dep_Time": "HH:MM", "Dep_Place": "City",
                            "Arr_Date": "DD-MM-YYYY", "Arr_Time": "HH:MM", "Arr_Place": "City",
                            "Mode": "Bus/Rail/Air/Private Vehicle/Official Car",
                            "Class": "AC-2/Sleeper/Economy/etc",
                            "Ticket_Amount": 0.0,
                            "Enquiry_Fare_If_Private": 0.0,
                            "Vehicle_Details": "e.g. GJ-05-AB-1234 Diesel (Only if Private)",
                            "Remark": ""
                        }
                    ]
                    
                    LOGIC:
                    1. If "Private Vehicle" is used, Ticket_Amount is usually 0, but look for documents saying "Enquiry Fare" or "GSRT Fare" and put that value in "Enquiry_Fare_If_Private".
                    2. Arrange chronologically.
                    """
                    
                    res = get_gemini_response(prompt, content, api_key, "json")
                    try:
                        data = json.loads(res)
                        st.session_state.diary_entries = pd.DataFrame(data)
                        st.success("Tour Diary Generated! Go to Tab 2 to edit.")
                    except Exception as e:
                        st.error(f"AI Error: {e}")

# --- TAB 2: MASTER DATA ENTRY ---
with tabs[1]:
    st.header("📝 Tour Diary (Chronological)")
    st.info("""
    **Instructions:**
    1. Enter rows chronologically (Departure -> Arrival).
    2. **Private Vehicle Users:** You MUST enter the 'Enquiry Fare' (Public Transport equivalent) in the specific column.
    3. **Stay:** If you stayed in a hotel, ensure the arrival at hotel and departure from hotel are clear in the timeline if claiming specific stay bills, or simply ensure the 'Arr_Date' and next 'Dep_Date' show the gap for DA calculation.
    """)
    
    # Column configuration for better UI
    column_config = {
        "Dep_Date": st.column_config.DateColumn("Dep Date", format="DD-MM-YYYY"),
        "Dep_Time": st.column_config.TimeColumn("Dep Time", format="HH:mm"),
        "Arr_Date": st.column_config.DateColumn("Arr Date", format="DD-MM-YYYY"),
        "Arr_Time": st.column_config.TimeColumn("Arr Time", format="HH:mm"),
        "Mode": st.column_config.SelectboxColumn("Mode", options=["Rail", "Bus", "Air", "Private Vehicle", "Govt Vehicle", "Auto/Taxi"]),
        "Ticket_Amount": st.column_config.NumberColumn("Actual Paid (Rs)", help="Amount on the ticket"),
        "Enquiry_Fare_If_Private": st.column_config.NumberColumn("Enquiry Fare (Rs)", help="MANDATORY if Private Vehicle used. The cost of Bus/Train for this route."),
        "Vehicle_Details": st.column_config.TextColumn("Vehicle Details", help="If Private: e.g. Diesel Car GJ-12..."),
    }

    edited_diary = st.data_editor(
        st.session_state.diary_entries,
        num_rows="dynamic",
        use_container_width=True,
        column_config=column_config,
        key="diary_editor"
    )
    st.session_state.diary_entries = edited_diary

# --- TAB 3: CALCULATION & REPORT ---
with tabs[2]:
    st.header("💰 Calculation & Justification")
    
    # --- ACTION BUTTON ---
    if st.button("🤖 Run AI Compliance Check & Calculate"):
        if not api_key:
            st.error("Please enter API Key")
        else:
            with st.spinner("Consulting Statutes & Calculating..."):
                rules_txt = load_rules_context()
                
                # Context Construction
                payload = {
                    "salary": st.session_state.salary_info,
                    "diary": st.session_state.diary_entries.to_dict(orient="records")
                }
                
                prompt = f"""
                Act as the NAU University Auditor. Based on the RULES provided and the TOUR DIARY, calculate TA and DA.

                **DEFINITIONS (from University Statutes):**
                1. **Ticket Price:** Actual fare paid.
                2. **Private Vehicle:** Reimbursement is RESTRICTED to the 'Enquiry Fare' (Public Transport Rate). Private mileage is NOT given.
                3. **DA:** Based on Pay Level and City Class (X, Y, Z).
                
                **YOUR TASK:**
                Return a JSON object with two keys: "ta_table" and "da_table".
                
                "ta_table": List of objects [
                    {{
                        "Route": "Place A to Place B",
                        "Mode_Used": "Private Vehicle", 
                        "Claimed_Fare": 0, 
                        "Admissible_Fare": 500, 
                        "Rule_Applied": "Restricted to Public Transport Fare", 
                        "Justification": "Private vehicle used, limited to Enquiry Fare as per Rule X."
                    }}
                ]
                
                "da_table": List of objects [
                    {{
                        "Date": "DD-MM-YYYY", 
                        "City": "Surat", 
                        "City_Class": "Y", 
                        "DA_Rate": 800, 
                        "Days_Claimable": 1, 
                        "Total_DA": 800, 
                        "Rule_Applied": "Pay Level 12 / Class Y",
                        "Justification": "Full day absence in Y class city."
                    }}
                ]
                
                DATA:
                {json.dumps(payload)}
                
                RULES CONTEXT:
                {rules_txt[:40000]}
                """
                
                res = get_gemini_response(prompt, [], api_key, "json")
                try:
                    calcs = json.loads(res)
                    st.session_state.ta_calc_table = pd.DataFrame(calcs["ta_table"])
                    st.session_state.da_calc_table = pd.DataFrame(calcs["da_table"])
                    st.success("Calculations Completed based on Rules!")
                except Exception as e:
                    st.error(f"Calculation Parsing Error: {e}")

    # --- SECTION A: TRAVEL ALLOWANCE (TA) ---
    st.subheader("A. Travel Allowance (TA) Calculation")
    st.caption("Verify the 'Admissible Fare' and the 'Rule Applied'. Edit if necessary.")
    
    edited_ta = st.data_editor(
        st.session_state.ta_calc_table,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "Admissible_Fare": st.column_config.NumberColumn("Admissible Amt (Rs)", required=True),
            "Justification": st.column_config.TextColumn("Reason / Rule", width="large")
        }
    )
    st.session_state.ta_calc_table = edited_ta
    
    total_ta = pd.to_numeric(edited_ta["Admissible_Fare"], errors='coerce').sum()
    st.metric("Total TA Admissible", f"₹ {total_ta:,.2f}")

    st.divider()

    # --- SECTION B: DAILY ALLOWANCE (DA) ---
    st.subheader("B. Daily Allowance (DA) Calculation")
    st.caption("Verify DA Rate and Days. The 'Rule Applied' column explains the rate choice.")
    
    edited_da = st.data_editor(
        st.session_state.da_calc_table,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "Total_DA": st.column_config.NumberColumn("Total DA (Rs)", required=True),
            "Justification": st.column_config.TextColumn("Reason / Rule", width="large")
        }
    )
    st.session_state.da_calc_table = edited_da
    
    total_da = pd.to_numeric(edited_da["Total_DA"], errors='coerce').sum()
    st.metric("Total DA Admissible", f"₹ {total_da:,.2f}")
    
    st.divider()
    st.markdown(f"### 🏁 GRAND TOTAL CLAIM: ₹ {total_ta + total_da:,.2f}")

    # --- PDF EXPORT ---
    if st.button("📄 Download NAU Tour Diary PDF"):
        
        class PDF(FPDF):
            def header(self):
                self.set_font('Arial', 'B', 12)
                self.cell(0, 10, 'NAVSARI AGRICULTURAL UNIVERSITY', 0, 1, 'C')
                self.set_font('Arial', 'B', 10)
                self.cell(0, 10, 'TRAVELLING ALLOWANCE BILL / TOUR DIARY', 0, 1, 'C')
                self.ln(5)

        pdf = PDF(orientation='L', unit='mm', format='A4') # Landscape for wide table
        pdf.add_page()
        pdf.set_font("Arial", size=9)
        
        # User Header Info
        designation = st.session_state.salary_info.get("Designation", "")
        pay = st.session_state.salary_info.get("Basic Pay", "")
        pdf.cell(0, 8, f"Name & Designation: {designation} | Basic Pay: {pay}", 0, 1)
        pdf.ln(5)
        
        # Table Header
        # Columns based on "Tour Diary" PDF
        # Sr, Dep(Place,Date,Time), Arr(Place,Date,Time), Mode, Class, TicketAmt, VehicleDetails, DA(Days,Rate,Amt), Total
        headers = ["Dep Place", "Dep Date", "Time", "Arr Place", "Arr Date", "Time", "Mode", "Class", "Fare (Rs)", "Vehicle/Petrol Details", "DA Days", "DA Rate", "DA Amt", "Total"]
        col_widths = [25, 20, 12, 25, 20, 12, 20, 15, 18, 40, 15, 15, 18, 20]
        
        pdf.set_font("Arial", 'B', 8)
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 10, h, 1, 0, 'C')
        pdf.ln()
        
        # Table Rows
        # We need to map the Diary Entries + Calculated DA to this row structure.
        # This is a bit complex because DA might be calculated per day, but the diary is per trip.
        # For simplicity in this demo, we will print the Diary Rows and fill DA where available.
        
        pdf.set_font("Arial", size=8)
        
        diary = st.session_state.diary_entries
        
        for idx, row in diary.iterrows():
            # Format Data
            d_date = str(row.get("Dep_Date", ""))
            d_time = str(row.get("Dep_Time", ""))
            d_place = str(row.get("Dep_Place", ""))[:15]
            
            a_date = str(row.get("Arr_Date", ""))
            a_time = str(row.get("Arr_Time", ""))
            a_place = str(row.get("Arr_Place", ""))[:15]
            
            mode = str(row.get("Mode", ""))[:10]
            cls = str(row.get("Class", ""))[:8]
            
            # Fare Logic: If Private, show Enquiry Fare
            fare = row.get("Ticket_Amount", 0)
            details = str(row.get("Vehicle_Details", ""))
            
            if "private" in mode.lower():
                fare = row.get("Enquiry_Fare_If_Private", 0)
                if not details or details == "nan": details = "Pvt Veh (Enquiry Fare)"
            
            # Simple line height
            h = 8
            
            pdf.cell(col_widths[0], h, d_place, 1)
            pdf.cell(col_widths[1], h, d_date, 1)
            pdf.cell(col_widths[2], h, d_time, 1)
            pdf.cell(col_widths[3], h, a_place, 1)
            pdf.cell(col_widths[4], h, a_date, 1)
            pdf.cell(col_widths[5], h, a_time, 1)
            pdf.cell(col_widths[6], h, mode, 1)
            pdf.cell(col_widths[7], h, cls, 1)
            pdf.cell(col_widths[8], h, str(fare), 1)
            pdf.cell(col_widths[9], h, details[:25], 1)
            
            # DA Columns (Leaving blank or finding match - simplified here to allow manual fill on paper if complex)
            # In a full production app, you'd match the DA table dates to these rows.
            pdf.cell(col_widths[10], h, "", 1) # DA Days
            pdf.cell(col_widths[11], h, "", 1) # Rate
            pdf.cell(col_widths[12], h, "", 1) # Amt
            pdf.cell(col_widths[13], h, "", 1) # Total
            
            pdf.ln()

        pdf.ln(10)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 10, f"TOTAL CLAIM ADMISSIBLE (Calculated by App): Rs. {total_ta + total_da}", 0, 1)
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(0, 10, "Note: This is a computer-generated assistance draft. Please attach original tickets.", 0, 1)

        pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore')
        st.download_button("Download PDF", pdf_bytes, "NAU_Tour_Diary.pdf", "application/pdf")

