import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import os
from PIL import Image
import PyPDF2
from docx import Document
from docx.shared import Inches, Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

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
    # Updated columns to match Tour Diary requirements (Dep/Arr split)
    st.session_state.tour_data = pd.DataFrame(columns=[
        "Dep_Date", "Dep_Time", "Dep_Place",
        "Arr_Date", "Arr_Time", "Arr_Place",
        "Mode", "Class", "Ticket_Amount", 
        "Road_Vehicle_Type", "Road_KM", "Road_Rate", "Road_Total",
        "Remark"
    ])

if "stay_data" not in st.session_state:
    st.session_state.stay_data = pd.DataFrame(columns=[
        "CheckIn_Date", "CheckIn_Time", 
        "CheckOut_Date", "CheckOut_Time", 
        "City", "Stay_Type", "Bill_Amount", "Claimable_Amount"
    ])

if "salary_info" not in st.session_state:
    st.session_state.salary_info = {"Basic Pay": 0, "Pay Level": "Level 12", "Designation": "Associate Professor"}

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
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except:
        return ""

def save_data():
    """Persist data to local JSON"""
    data = {
        "tour": st.session_state.tour_data.to_dict(orient="records"),
        "stay": st.session_state.stay_data.to_dict(orient="records"),
        "salary": st.session_state.salary_info
    }
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f)

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

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    
    st.divider()
    st.subheader("📋 Employee Details")
    st.session_state.salary_info["Designation"] = st.text_input("Designation", st.session_state.salary_info.get("Designation", ""))
    st.session_state.salary_info["Pay Level"] = st.selectbox("Pay Level", ["Level 14", "Level 13A", "Level 13", "Level 12", "Level 11", "Level 10", "Level 9", "Level 8", "Level 7"], index=3)
    st.session_state.salary_info["Basic Pay"] = st.number_input("Basic Pay", value=st.session_state.salary_info.get("Basic Pay", 0))

# --- MAIN APP ---
st.title("🚜 NAU TA/DA Reimbursement Assistant")

tabs = st.tabs(["1. Upload Proofs", "2. Edit Data (Tour/Stay)", "3. Export Tour Diary (Docx)"])

# --- TAB 1: UPLOADS & EXTRACTION ---
with tabs[0]:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Step 1: Salary Slip (Optional)")
        salary_file = st.file_uploader("Upload Salary Slip", type=["pdf", "jpg", "png"])
        if salary_file and st.button("Extract Salary Info"):
            if not api_key:
                st.error("Please enter API Key")
            else:
                with st.spinner("Analyzing Salary Slip..."):
                    content = []
                    if salary_file.type == "application/pdf":
                        content.append(extract_text_from_pdf(salary_file))
                    else:
                        content.append(Image.open(salary_file))
                    
                    prompt = """Extract: {"Basic Pay": number, "Pay Level": "string", "Designation": "string"}"""
                    res = get_gemini_response(prompt, content, api_key)
                    try:
                        clean_json = res.replace("```json", "").replace("```", "")
                        extracted = json.loads(clean_json)
                        st.session_state.salary_info.update(extracted)
                        st.success("Extracted!")
                    except:
                        st.error("Manual entry required.")

    with col2:
        st.subheader("Step 2: Tour Diary / Tickets")
        tour_files = st.file_uploader("Upload Diary/Tickets", accept_multiple_files=True)
        
        if tour_files and st.button("Auto-Fill Journey"):
            if not api_key:
                st.error("Need API Key")
            else:
                with st.spinner("Extracting Journey Details..."):
                    combined_content = ["Extract chronological journey legs."]
                    for tf in tour_files:
                        if tf.type == "application/pdf":
                            combined_content.append(extract_text_from_pdf(tf))
                        else:
                            combined_content.append(Image.open(tf))
                    
                    # Updated prompt to get split Date/Time and Places
                    prompt = """
                    Extract travel legs into JSON list.
                    Format: [
                        {
                            "Dep_Date": "YYYY-MM-DD", "Dep_Time": "HH:MM", "Dep_Place": "City",
                            "Arr_Date": "YYYY-MM-DD", "Arr_Time": "HH:MM", "Arr_Place": "City",
                            "Mode": "Bus/Rail/Air/Private/Official", 
                            "Ticket_Amount": 0,
                            "Road_Vehicle_Type": "Diesel/Petrol/None",
                            "Road_KM": 0,
                            "Remark": ""
                        }
                    ]
                    Rules: 
                    1. Separate Departure and Arrival times explicitly.
                    2. If Private Vehicle used, note 'Diesel' or 'Petrol' if available.
                    """
                    
                    res = get_gemini_response(prompt, combined_content, api_key)
                    try:
                        clean_json = res.replace("```json", "").replace("```", "")
                        new_data = pd.DataFrame(json.loads(clean_json))
                        # Align columns
                        for col in st.session_state.tour_data.columns:
                            if col not in new_data.columns:
                                new_data[col] = None
                        st.session_state.tour_data = new_data
                        st.success("Journey Data Extracted!")
                        save_data()
                    except Exception as e:
                        st.error(f"Error parsing AI response: {e}")

# --- TAB 2: DATA ENTRY ---
with tabs[1]:
    st.header("📝 Edit Journey & Stay Details")
    
    st.subheader("A. Tour Journey (Chronological)")
    st.info("Arrange your journey by Date/Time. Ensure 'Departure' and 'Arrival' columns are correct.")
    
    # Configure columns for the editor
    column_config = {
        "Dep_Date": st.column_config.DateColumn("Dep Date"),
        "Dep_Time": st.column_config.TimeColumn("Dep Time", format="HH:mm"),
        "Dep_Place": st.column_config.TextColumn("Dep Place"),
        "Arr_Date": st.column_config.DateColumn("Arr Date"),
        "Arr_Time": st.column_config.TimeColumn("Arr Time", format="HH:mm"),
        "Arr_Place": st.column_config.TextColumn("Arr Place"),
        "Mode": st.column_config.SelectboxColumn("Mode", options=["Railway", "Bus", "Flight", "Private Vehicle", "Official Vehicle", "Taxi/Auto"]),
        "Road_Vehicle_Type": st.column_config.SelectboxColumn("Fuel/Vehicle", options=["Petrol Car", "Diesel Car", "Taxi", "Auto", "None"], help="Required for Road Travel by Other Vehicle"),
        "Ticket_Amount": st.column_config.NumberColumn("Ticket (Rs)"),
        "Road_Total": st.column_config.NumberColumn("Road Total (Rs)"),
    }
    
    edited_tour = st.data_editor(
        st.session_state.tour_data, 
        column_config=column_config,
        num_rows="dynamic",
        use_container_width=True,
        key="tour_edit"
    )
    st.session_state.tour_data = edited_tour
    
    st.divider()
    
    st.subheader("B. Stay / Accommodation")
    stay_config = {
        "CheckIn_Date": st.column_config.DateColumn("Check-In"),
        "CheckOut_Date": st.column_config.DateColumn("Check-Out"),
        "City": st.column_config.TextColumn("City"),
        "Stay_Type": st.column_config.SelectboxColumn("Type", options=["Hotel", "Guest House", "Own"]),
        "Bill_Amount": st.column_config.NumberColumn("Bill Amount")
    }
    
    edited_stay = st.data_editor(
        st.session_state.stay_data, 
        column_config=stay_config, 
        num_rows="dynamic", 
        use_container_width=True,
        key="stay_edit"
    )
    st.session_state.stay_data = edited_stay
    
    if st.button("💾 Save All Changes"):
        save_data()
        st.toast("Changes Saved!")

# --- TAB 3: EXPORT ---
with tabs[2]:
    st.header("📄 Export Tour Diary (Docx)")
    st.caption("Generates a Word document matching the 'Tour Diary' format with definitions attached.")
    
    if st.button("Generate Word Document"):
        # Create Document
        doc = Document()
        
        # --- TITLE ---
        heading = doc.add_heading('NAU TOUR DIARY', 0)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # --- EMPLOYEE INFO ---
        p = doc.add_paragraph()
        p.add_run(f"Name: Vaibhav Kumar Kanubhai Chaudhari\n").bold = True # Example Name
        p.add_run(f"Designation: {st.session_state.salary_info.get('Designation', '')}\n")
        p.add_run(f"Pay Level: {st.session_state.salary_info.get('Pay Level', '')}\n")
        p.add_run(f"Basic Pay: {st.session_state.salary_info.get('Basic Pay', '')}")
        
        # --- TABLE SETUP ---
        # Columns based on "Tour Diary" PDF structure
        # 0: Sr No, 1: Dep Place, 2: Dep Date/Time, 3: Arr Place, 4: Arr Date/Time, 
        # 5: Mode, 6: Class, 7: Ticket Amt, 8: Road(Fuel), 9: Road(Rate/KM), 10: Road(Total)
        
        doc.add_heading('Journey Details', level=2)
        
        table = doc.add_table(rows=1, cols=11)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "Sr."
        hdr_cells[1].text = "Departure\nPlace"
        hdr_cells[2].text = "Departure\nDate & Time"
        hdr_cells[3].text = "Arrival\nPlace"
        hdr_cells[4].text = "Arrival\nDate & Time"
        hdr_cells[5].text = "Mode"
        hdr_cells[6].text = "Class"
        hdr_cells[7].text = "Ticket\n(Rs)"
        hdr_cells[8].text = "Road Vehicle\n(Petrol/Diesel)"
        hdr_cells[9].text = "Road\n(KM / Rate)"
        hdr_cells[10].text = "Total\n(Rs)"
        
        # Sort by date
        df_sorted = st.session_state.tour_data.sort_values(by="Dep_Date")
        
        total_claim = 0
        
        for idx, row in df_sorted.iterrows():
            row_cells = table.add_row().cells
            row_cells[0].text = str(idx + 1)
            row_cells[1].text = str(row['Dep_Place'])
            row_cells[2].text = f"{row['Dep_Date']}\n{row['Dep_Time']}"
            row_cells[3].text = str(row['Arr_Place'])
            row_cells[4].text = f"{row['Arr_Date']}\n{row['Arr_Time']}"
            row_cells[5].text = str(row['Mode'])
            row_cells[6].text = str(row['Class']) if row['Class'] else "-"
            
            # Ticket Amount
            t_amt = float(row['Ticket_Amount']) if row['Ticket_Amount'] else 0
            row_cells[7].text = str(t_amt) if t_amt > 0 else "-"
            
            # Road Details
            row_cells[8].text = str(row['Road_Vehicle_Type']) if row['Road_Vehicle_Type'] else "-"
            
            km = row.get('Road_KM', 0)
            rate = row.get('Road_Rate', 0)
            if km and float(km) > 0:
                row_cells[9].text = f"{km} km\n@{rate}/km"
            else:
                row_cells[9].text = "-"
                
            # Total Calculation logic
            road_total = float(row['Road_Total']) if row['Road_Total'] else 0
            line_total = t_amt + road_total
            row_cells[10].text = str(line_total)
            
            total_claim += line_total
            
        # Add Total Row
        row_cells = table.add_row().cells
        row_cells[9].text = "GRAND TOTAL:"
        row_cells[10].text = str(total_claim)
        
        # --- DEFINITIONS SECTION ---
        doc.add_page_break()
        doc.add_heading('DEFINITIONS & INSTRUCTIONS', level=2)
        
        definitions = [
            ("Mode of Transport (Railway / Bus / Flight)", 
             "Means the actual means of conveyance used by the employee for performing the journey on official tour, such as Railway, Public Bus, or Air, as recorded in the tour diary and supported by valid travel documents."),
            
            ("Class of Travel (I / II / III)", 
             "Means the category of travel entitlement applicable to a University employee for performing a journey on official tour, such as First Class, Second Class, or Third Class, as per the employee’s pay level, designation, and eligibility prescribed under the Travelling Allowance Rules."),
            
            ("Ticket Price / Rate (Rs.)", 
             "Means the actual fare paid in rupees for travel by the entitled mode and class for performing a journey on official tour, as supported by the original travel ticket, receipt, or authorised proof of fare. Where the original ticket or receipt is not available, the fare determined through an official fare enquiry from the Railway / State Transport Bus / Airline for the same date, route, and eligible class of travel may be considered for the purpose of Travelling Allowance calculation, subject to admissibility under the rules and certification by the competent authority."),
            
            ("Road Travel by Other Vehicle", 
             "Means travel performed on official tour by a mode of road transport other than Railway or Air, such as State Transport Bus, Metro, Auto-rickshaw, Taxi, or other public conveyance, used for the journey between places connected by road. In cases where travel is performed by a motor vehicle powered by diesel or petrol, the type of vehicle and fuel used shall be clearly indicated in the tour diary.\n\nHowever, use of a private vehicle is not ordinarily admissible for reimbursement in the University, and in such cases, Travelling Allowance shall be restricted to the fare determined through an official fare enquiry of the eligible public transport for the same route and distance. Reimbursement for road travel shall be regulated on the basis of fare enquiry or admissible public conveyance rates, and not on the basis of private vehicle ownership, even though provisions for road mileage exist under the rules.\n\nTravel by auto-rickshaw, metro rail, city bus, or other recognised public transport is admissible for calculation of Travelling Allowance, subject to necessity, reasonableness, and certification in the tour diary."),
            
            ("Days of Daily Allowance receivable", 
             "Means the number of days for which Daily Allowance (DA) is admissible to a University employee while on tour, determined on the basis of the total duration of absence from headquarters, including journey time, and calculated in accordance with the minimum time limits prescribed under the Travelling Allowance Rules."),
            
            ("Daily Allowance Rate (Rs.)", 
             "Means the monetary rate of Daily Allowance prescribed in rupees and applicable to a University employee for a day of tour, determined on the basis of the employee’s pay level/grade and the classification of the city or place of halt, as notified under the Travelling Allowance provisions.")
        ]
        
        for title, text in definitions:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(12)
            run = p.add_run(f"{title}: ")
            run.bold = True
            run.font.size = Pt(11)
            p.add_run(text)
            
        # --- DOWNLOAD BUTTON ---
        from io import BytesIO
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        st.download_button(
            label="📥 Download Tour Diary (.docx)",
            data=buffer,
            file_name="NAU_Tour_Diary.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
