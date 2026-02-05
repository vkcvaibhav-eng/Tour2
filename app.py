import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import os
from PIL import Image
import PyPDF2
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches, Cm
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
    st.session_state.tour_data = pd.DataFrame(columns=[
        "Date", "From", "To", "Mode", "Distance_KM", 
        "Ticket_Amount", "Enquiry_Fare_If_Private", "Remark", 
        "Departure_Time", "Arrival_Time" # Added for better form filling
    ])
if "stay_data" not in st.session_state:
    st.session_state.stay_data = pd.DataFrame(columns=[
        "Date_CheckIn", "Date_CheckOut", "Hotel_Name", 
        "City", "Bill_Amount", "Claimable_Amount"
    ])
if "salary_info" not in st.session_state:
    st.session_state.salary_info = {
        "Basic Pay": 0, 
        "Pay Level": "", 
        "Designation": "Associate Professor", 
        "Name": "V. K. Chaudhari",
        "Department": "Agricultural Entomology"
    }

# --- HELPER FUNCTIONS ---

def get_gemini_response(prompt, content_parts, api_key):
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

def save_data():
    data = {
        "tour": st.session_state.tour_data.to_dict(orient="records"),
        "stay": st.session_state.stay_data.to_dict(orient="records"),
        "salary": st.session_state.salary_info
    }
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f)
    st.toast("Data Saved Successfully!")

def load_data():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
            st.session_state.tour_data = pd.DataFrame(data.get("tour", []))
            st.session_state.stay_data = pd.DataFrame(data.get("stay", []))
            st.session_state.salary_info = data.get("salary", {})

# --- WORD GENERATION FUNCTION ---
def create_word_report(tour_data, stay_data, salary_info):
    doc = Document()
    
    # Set Margins (Narrow)
    sections = doc.sections
    for section in sections:
        section.top_margin = Cm(1.5)
        section.bottom_margin = Cm(1.5)
        section.left_margin = Cm(1.5)
        section.right_margin = Cm(1.5)

    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(10)

    # --- PAGE 1: BILL SUMMARY ---
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run("હિસાબી પત્રક નંબર: ________\nબીલ નંબર: ________\nતારીખ: ________")
    
    title = doc.add_paragraph("નવસારી કૃષિ વિશ્વવિધાલય\nમુસાફરી ભથ્થા બીલ")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.runs[0].bold = True
    title.runs[0].font.size = Pt(14)

    info_table = doc.add_table(rows=1, cols=2)
    info_table.autofit = True
    info_table.style = 'Table Grid'
    
    # Helper to add rows to info table
    def add_info_row(label, value):
        row = info_table.add_row().cells
        row[0].text = label
        row[1].text = str(value)

    add_info_row("કર્મચારીનું નામ", salary_info.get("Name", "V. K. Chaudhari"))
    add_info_row("હોદ્દો", salary_info.get("Designation", "Associate Professor"))
    add_info_row("કચેરી", salary_info.get("Department", "Agricultural Entomology"))
    add_info_row("હેડ ક્વાર્ટર", "Navsari")
    add_info_row("બેઝીક પગાર", str(salary_info.get("Basic Pay", "")))
    add_info_row("પગાર ધોરણ (Level)", str(salary_info.get("Pay Level", "")))

    doc.add_paragraph("\n")
    
    # Receipt / Approval Block
    p = doc.add_paragraph()
    p.add_run("આથી રૂ. __________________ (અંકે રૂપિયા __________________________________ પુરા) નો દાવો મંજુર કરી ગ્રાહય રાખવામાં આવે છે.")
    doc.add_paragraph("\n\n")
    
    sig_table = doc.add_table(rows=1, cols=2)
    sig_table.width = Inches(6)
    c = sig_table.rows[0].cells
    c[0].text = "સ્થળ: નવસારી\nતારીખ: "
    c[1].text = "બીલ મંજુર કરનાર અધિકારીની\nસહી અને હોદ્દો"
    c[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_page_break()

    # --- PAGE 2: TABLE PART 1 (Cols 1-9) ---
    p = doc.add_paragraph("Table Part A: Journey Details")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Columns 1-9 Headers
    headers_1 = ["1. No", "2. Station From", "3. Date/Time", "4. Station To", "5. Date/Time", "6. Mode", "7. Class", "8. Ticket No", "9. Fare (Rs)"]
    
    t1 = doc.add_table(rows=1, cols=9)
    t1.style = 'Table Grid'
    hdr_cells = t1.rows[0].cells
    for i, h in enumerate(headers_1):
        hdr_cells[i].text = h
        hdr_cells[i].paragraphs[0].runs[0].font.bold = True
        hdr_cells[i].paragraphs[0].runs[0].font.size = Pt(8)

    # Fill Data
    idx = 1
    total_fare = 0
    for _, row in tour_data.iterrows():
        cells = t1.add_row().cells
        # Logic to handle Private Vehicle Fare vs Ticket
        fare = row.get("Ticket_Amount", 0)
        mode = str(row.get("Mode", "")).lower()
        if "private" in mode or "car" in mode:
             fare = row.get("Enquiry_Fare_If_Private", 0)
        try:
            total_fare += float(fare)
        except:
            pass

        cells[0].text = str(idx)
        cells[1].text = str(row.get("From", ""))
        cells[2].text = str(row.get("Date", ""))  # User can edit this to include time in app
        cells[3].text = str(row.get("To", ""))
        cells[4].text = str(row.get("Date", ""))
        cells[5].text = str(row.get("Mode", ""))
        cells[6].text = "Ord" # Placeholder class
        cells[7].text = "-"
        cells[8].text = str(fare)
        idx += 1

    doc.add_paragraph("\n")
    cert = doc.add_paragraph("This is to certify that above said TA bill is prepared based on actual journey and actual destination.")
    cert.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_page_break()

    # --- PAGE 3: TABLE PART 2 (Cols 10-19) ---
    p = doc.add_paragraph("Table Part B: Calculation")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Columns 10-19 Headers
    headers_2 = ["10. Road Km", "11. Rate", "12. Amt", "13. DA Days", "14. DA Rate", "15. Total DA", "16. Total (10+12+15)", "17. Purpose", "18. Remarks"]
    
    t2 = doc.add_table(rows=1, cols=9)
    t2.style = 'Table Grid'
    hdr_cells = t2.rows[0].cells
    for i, h in enumerate(headers_2):
        hdr_cells[i].text = h
        hdr_cells[i].paragraphs[0].runs[0].font.bold = True
        hdr_cells[i].paragraphs[0].runs[0].font.size = Pt(8)

    # Fill Data (Must match row count of Page 2)
    grand_total = 0
    for _, row in tour_data.iterrows():
        cells = t2.add_row().cells
        
        # Placeholders for calculation (since these are usually done by the user or the AI text report)
        # In a full app, we would calculate these in Python before generating Word
        fare = row.get("Ticket_Amount", 0)
        if "private" in str(row.get("Mode", "")).lower():
             fare = row.get("Enquiry_Fare_If_Private", 0)
        
        cells[0].text = "-" # Road Km
        cells[1].text = "-" # Rate
        cells[2].text = "-" # Road Amt
        cells[3].text = "" # DA Days
        cells[4].text = "" # DA Rate
        cells[5].text = "" # Total DA
        cells[6].text = str(fare) # Total Row (Approx)
        cells[7].text = "Official Work" # Purpose
        cells[8].text = str(row.get("Remark", ""))
        
        try:
            grand_total += float(fare)
        except:
            pass

    # Total Row
    row = t2.add_row().cells
    row[5].text = "GRAND TOTAL:"
    row[6].text = str(grand_total)

    doc.add_paragraph("\n\n")
    sig = doc.add_paragraph(f"({salary_info.get('Name', 'V. K. Chaudhari')})")
    sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_page_break()

    # --- PAGE 4: CERTIFICATES & FINAL SUMMARY ---
    doc.add_paragraph("નોંધ :- (૧) કોલમ નં. ૭ માં મુસાફરી પ્રકાર રેલ્વે/એસ.ટી./હવાઈ/સ્ટીમર/ભાડાનું યુનિવર્સિટી કે સરકારી કે પોતાનું વાહન ઈત્યાદી મારફત કરેલ મુસાફરીની સ્પષ્ટ નોંધ આપવી.")
    
    doc.add_paragraph("\nયુનિવર્સિટી કર્મચારીએ આપવાનું પ્રમાણપત્ર", style='Intense Quote')
    
    certs = [
        "(૧) આથી પ્રમાણપત્ર આપવામાં આવે છે કે, આ બીલમાં આકારેલ રકમ બીજા કોઈ બીલમાં આકારેલ નથી.",
        "(૨) આથી પ્રમાણીત કરવામાં આવે છે કે સદર મુસાફરી ભથ્થ બીલમાં દર્શાવેલ હકીકત સાચી છે.",
        "(૩) આથી પ્રમાણપત્ર આપવામાં આવે છે કે બીલમાં દર્શાવેલ પ્રવાસ માટે મેં આ અગાઉ પેશગી લીધેલ નથી.",
        "(૪) આ બીલમાં જણાવેલ યુનિવર્સિટી સિવાયની અન્ય સંસ્થાની કામગીરીના પ્રવાસ માટે જે તે સંસ્થા તરફથી નાણાં મળેલ નથી.",
        "(૫) આથી પ્રમાણપત્ર આપવામાં આવે છે કે, પ્રવાસ ડાયરીમાં દર્શાવવામાં આવેલ સ્થળ, તારીખ, સમય, કિલોમીટર સાચા છે."
    ]
    for c_text in certs:
        doc.add_paragraph(c_text)

    doc.add_paragraph("\n\n")
    
    # Signatures Table
    sig_tab = doc.add_table(rows=1, cols=2)
    sig_tab.width = Inches(7)
    
    c1 = sig_tab.cell(0, 0)
    c1.text = "યુનિવર્સિટી અધિકારીઓ અને અન્ય સભ્યોએ આપવાનું પ્રમાણપત્ર\n\n\n\nપ્રાધ્યાપક અને વડા\nકિટકશાસ્ત્ર વિભાગ\nનં. મ. કૃષિ મહાવિદ્યાલય\nનકૃયું, નવસારી"
    
    c2 = sig_tab.cell(0, 1)
    # Right align the user signature
    p = c2.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run(f"\n\n\n({salary_info.get('Name', 'V. K. Chaudhari')})\n{salary_info.get('Designation', 'Associate Professor')}")

    doc.add_paragraph("\n")
    
    # Final Summary Table (Bottom of Page 4)
    doc.add_paragraph("કર્મચારી / અધિકારી / સભ્યશ્રીએ નીચેની વિગત ભરવી.")
    final_table = doc.add_table(rows=4, cols=3)
    final_table.style = 'Table Grid'
    
    ft_data = [
        ["બીલની કુલ રકમ", ":", str(grand_total)],
        ["બાદ: પેશગીની રકમ", ":", "0"],
        ["ચૂકવવા પાત્ર ચોખ્ખી રકમ", ":", str(grand_total)],
        ["પેશગી લીધા તારીખ", ":", "-"]
    ]
    
    for i, row_data in enumerate(ft_data):
        cells = final_table.rows[i].cells
        cells[0].text = row_data[0]
        cells[1].text = row_data[1]
        cells[2].text = row_data[2]

    # Save to BytesIO
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# Load saved data on startup
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

tabs = st.tabs(["1. Upload Proofs", "2. Edit Data", "3. Final Report & Word Export"])

# --- TAB 1: UPLOADS ---
with tabs[0]:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Step 1: Salary Slip")
        salary_file = st.file_uploader("Upload Salary Slip", type=["pdf", "jpg", "png"])
        if salary_file and st.button("Extract Salary"):
            if not api_key: st.error("Need API Key")
            else:
                st.session_state.salary_info["Name"] = "V. K. Chaudhari" # Auto-set per requirement
                st.success("Defaulted to V. K. Chaudhari / Ag. Entomology")

    with col2:
        st.subheader("Step 2: Tour Diary")
        tour_files = st.file_uploader("Upload Tour Docs", accept_multiple_files=True)
        if tour_files and st.button("Auto-Fill"):
            if not api_key: st.error("Need API Key")
            else:
                with st.spinner("Processing..."):
                    # Mocking extraction for the snippet - in real use, keep your existing logic
                    prompt = """Extract JSON list of trips: [{"Date": "DD-MM-YYYY", "From": "City", "To": "City", "Mode": "Bus/Rail/Private", "Ticket_Amount": 0, "Enquiry_Fare_If_Private": 0, "Remark": ""}]"""
                    # You would call get_gemini_response here
                    st.success("Tour data extracted (Mock)")

# --- TAB 2: EDIT ---
with tabs[1]:
    st.subheader("Edit Tour Details")
    st.session_state.tour_data = st.data_editor(
        st.session_state.tour_data, num_rows="dynamic", use_container_width=True
    )
    st.subheader("Edit User Profile")
    st.session_state.salary_info["Name"] = st.text_input("Name", st.session_state.salary_info.get("Name"))
    st.session_state.salary_info["Designation"] = st.text_input("Designation", st.session_state.salary_info.get("Designation"))
    save_data()

# --- TAB 3: EXPORT ---
with tabs[2]:
    st.header("📥 Download Final Word Document")
    st.info("This will generate the 4-Page Gujarati/English Word Document.")
    
    if st.button("Generate Word Bill"):
        word_file = create_word_report(
            st.session_state.tour_data, 
            st.session_state.stay_data, 
            st.session_state.salary_info
        )
        
        st.download_button(
            label="Download .docx Bill",
            data=word_file,
            file_name="NAU_TA_Bill_Final.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
