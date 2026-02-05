import os
import glob
import time
import pandas as pd
import google.generativeai as genai
from docx import Document
from docx.shared import Mm, Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL

# Directory for permanent rules
RULES_DIR = "rules_storage"
if not os.path.exists(RULES_DIR):
    os.makedirs(RULES_DIR)

def save_permanent_rule(uploaded_file):
    if uploaded_file is not None:
        file_path = os.path.join(RULES_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

def list_saved_rules():
    return [os.path.basename(x) for x in glob.glob(os.path.join(RULES_DIR, "*.pdf"))]

def call_gemini_extraction(api_key, trip_files, context_prompt):
    """
    Uses Gemini 1.5 Pro to extract data based on Statutes.
    """
    if not api_key:
        return {"error": "No API Key provided"}

    genai.configure(api_key=api_key)
    
    gemini_files = []
    # Upload Rules
    rule_paths = glob.glob(os.path.join(RULES_DIR, "*.pdf"))
    for path in rule_paths:
        g_file = genai.upload_file(path)
        gemini_files.append(g_file)

    # Upload Trip Files
    for f in trip_files:
        with open(f.name, "wb") as temp_f:
            temp_f.write(f.getbuffer())
        g_file = genai.upload_file(f.name)
        gemini_files.append(g_file)

    time.sleep(2) # Buffer for processing

    system_instruction = """
    You are a University Accountant.
    Calculate TA/DA based strictly on the uploaded Rules/Statutes.
    
    RETURN JSON ONLY.
    
    1. Identify User Pay Level from Salary Slip.
    2. Extract Tour Diary (Movement).
    3. Calculate TA (Fares) based on Pay Level entitlement.
    4. Calculate DA based on DURATION (Dispatch to Arrival).
    
    JSON Structure:
    {
      "user_details": {"name": "...", "pay_level": "...", "basic_pay": "..."},
      "tour_diary": [
        {"Dispatch_Station": "...", "Dispatch_Date": "...", "Dispatch_Hour": "...", 
         "Arrival_Station": "...", "Arrival_Date": "...", "Arrival_Hour": "...", 
         "Mode_of_Travel": "...", "Purpose": "..."}
      ],
      "ta_data": [
         {"Mode": "...", "Ticket_No": "...", "Fare_Amount": "...", "Distance_Km": "...", "Rate_Per_Km": "..."}
      ],
      "da_calculation": [
        {"Date": "...", "Duration_Hours": "...", "DA_Amount": "..."}
      ]
    }
    """
    model = genai.GenerativeModel(model_name="gemini-1.5-pro")
    try:
        response = model.generate_content([system_instruction, context_prompt, *gemini_files])
        return response.text
    except Exception as e:
        return {"error": str(e)}

def set_col_widths(table):
    """Helper to set column widths for the complex 16-col table"""
    widths = [0.8, 2.0, 1.8, 1.2, 2.0, 1.8, 1.2, 1.5, 1.0, 1.5, 1.5, 1.2, 1.2, 1.5, 1.0, 1.2, 1.5, 1.8, 2.5, 1.5]
    for row in table.rows:
        for idx, width in enumerate(widths):
            if idx < len(row.cells):
                row.cells[idx].width = Cm(width)

def create_complex_claim_form(diary_df, ta_df, da_df):
    """
    Generates the strict 1-16 Column format requested.
    Merges Diary, TA, and DA into one master table.
    """
    doc = Document()
    
    # A3 Landscape Setup
    section = doc.sections[0]
    section.page_width = Mm(420)
    section.page_height = Mm(297)
    section.left_margin = Mm(10)
    section.right_margin = Mm(10)
    
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(9) # Smaller font to fit 16 cols

    doc.add_heading('TA/DA Bill Claim Form', 0)

    # --- MASTER TABLE CREATION ---
    # We need 20 columns to accommodate Sr No + 16 Data Cols + Purpose + Note + Total
    # Specific Mapping based on user CSV:
    # 0: Sr No
    # 1-3: Departure (Place, Date, Time)
    # 4-6: Arrival (Place, Date, Time)
    # 7-10: Public Transport (Mode, Class, Ticket, Total)
    # 11-13: Road (KM, Rate, Total)
    # 14-16: DA (Days, Rate, Amt)
    # 17: Grand Total (10+13+16)
    # 18: Purpose
    # 19: Note

    table = doc.add_table(rows=2, cols=20)
    table.style = 'Table Grid'
    table.autofit = False 
    set_col_widths(table)

    # --- HEADER ROW 1 (Text) ---
    headers = [
        "Sr.\nNo.", 
        "Departure\nPlace", "Departure\nDate", "Departure\nTime",
        "Arrival\nPlace", "Arrival\nDate", "Arrival\nTime",
        "Mode\n(Rail/Bus)", "Class", "Ticket\nPrice", "Total\n(A)",
        "Road\nKM", "Rate", "Total\n(B)",
        "DA\nDays", "DA\nRate", "DA\nAmt",
        "TOTAL\n(A+B+DA)", "Purpose", "Note"
    ]
    
    hdr_cells = table.rows[0].cells
    for i, text in enumerate(headers):
        hdr_cells[i].text = text
        hdr_cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # --- HEADER ROW 2 (Numbers 1-16) ---
    # CSV maps: Place(1)..Time(3)..Place(4)..Time(6)..Mode(7)..Total(10)..KM(11)..Total(13)..Days(14)..Amt(16)
    num_map = ["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "", "", ""]
    num_cells = table.rows[1].cells
    for i, text in enumerate(num_map):
        num_cells[i].text = text
        num_cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # --- DATA MERGING LOGIC ---
    # We iterate through the Diary (Movement) as the primary index.
    # We try to find matching TA/DA data for that row index.
    
    row_count = len(diary_df)
    
    for index in range(row_count):
        row_cells = table.add_row().cells
        
        # 0. Sr No
        row_cells[0].text = str(index + 1)
        
        # 1-6. Tour Diary Data (Safe Get)
        if index < len(diary_df):
            d_row = diary_df.iloc[index]
            row_cells[1].text = str(d_row.get('Dispatch_Station', ''))
            row_cells[2].text = str(d_row.get('Dispatch_Date', ''))
            row_cells[3].text = str(d_row.get('Dispatch_Hour', ''))
            row_cells[4].text = str(d_row.get('Arrival_Station', ''))
            row_cells[5].text = str(d_row.get('Arrival_Date', ''))
            row_cells[6].text = str(d_row.get('Arrival_Hour', ''))
            purpose = str(d_row.get('Purpose', ''))
            mode_raw = str(d_row.get('Mode_of_Travel', '')).lower()
        else:
            mode_raw = ""
            purpose = ""

        # TA Data (Cols 7-13)
        # We check if 'ta_df' has a row for this index
        ta_val = 0
        road_val = 0
        
        if index < len(ta_df):
            t_row = ta_df.iloc[index]
            fare = float(pd.to_numeric(t_row.get('Fare_Amount', 0), errors='coerce') or 0)
            
            # Decide if it goes to Public (7-10) or Private Road (11-13)
            # Simple keyword check
            if "private" in mode_raw or "car" in mode_raw or "taxi" in mode_raw:
                # Fill Road Cols
                row_cells[11].text = str(t_row.get('Distance_Km', '')) # KM
                row_cells[12].text = str(t_row.get('Rate_Per_Km', '')) # Rate
                row_cells[13].text = str(fare) # Total Road
                road_val = fare
            else:
                # Fill Public Cols
                row_cells[7].text = str(t_row.get('Mode', ''))
                row_cells[8].text = "II/III" # Default or extract
                row_cells[9].text = str(fare)
                row_cells[10].text = str(fare) # Total Public
                ta_val = fare

        # DA Data (Cols 14-16)
        da_val = 0
        if index < len(da_df):
            da_row = da_df.iloc[index]
            da_amt = float(pd.to_numeric(da_row.get('DA_Amount', 0), errors='coerce') or 0)
            row_cells[14].text = str(da_row.get('Duration_Hours', '')) # Days/Hours
            row_cells[15].text = str(da_row.get('Rate_Applied', '')) # Rate
            row_cells[16].text = str(da_amt) # Amount
            da_val = da_amt
            
        # 17. Grand Total for Row
        row_total = ta_val + road_val + da_val
        row_cells[17].text = str(row_total)
        
        # 18. Purpose
        row_cells[18].text = purpose
        
        # 19. Note
        row_cells[19].text = ""

    return doc
