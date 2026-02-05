import os
import google.generativeai as genai
from docx import Document
from docx.shared import Mm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Ensure storage directory exists
RULES_DIR = "rules_storage"
if not os.path.exists(RULES_DIR):
    os.makedirs(RULES_DIR)

def save_permanent_rule(uploaded_file):
    """Saves a rule file permanently to the local disk."""
    if uploaded_file is not None:
        file_path = os.path.join(RULES_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

def list_saved_rules():
    """Lists all permanently saved rules."""
    return os.listdir(RULES_DIR)

def call_gemini_extraction(api_key, files, context_prompt):
    """
    Extracts strict Tour Diary columns: Station, Date, Hour.
    """
    if not api_key:
        return {"error": "No API Key provided"}

    # Configure Gemini
    genai.configure(api_key=api_key)
    
    # Upload files to Gemini
    uploaded_files = []
    for f in files:
        # Save temp file to upload
        with open(f.name, "wb") as temp_f:
            temp_f.write(f.getbuffer())
        
        # Upload to Gemini
        gf = genai.upload_file(f.name)
        uploaded_files.append(gf)

    # STRICT PROMPT for Tour Diary
    system_instruction = """
    You are an AI assistant for a University Professor.
    Your task is to extract travel data EXACTLY as it appears in the 'Tour Diary' document.
    
    RETURN JSON ONLY.
    
    Structure the data into three specific lists:
    1. "tour_diary": Extract strictly the columns:
       - 'Dispatch_Station', 'Dispatch_Date', 'Dispatch_Hour'
       - 'Arrival_Station', 'Arrival_Date', 'Arrival_Hour'
       - 'Mode_of_Travel', 'Distance_km', 'Purpose'
       
    2. "ta_data": Extract Ticket details found in the files:
       - 'Mode', 'Ticket_No', 'Fare_Amount'
       
    3. "da_data": Calculate purely based on dates:
       - 'Date', 'Stay_Location', 'Days_Claimed' (1 or 0.5)

    Do not change the station names. Keep them exactly as written in the diary.
    """
    
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    
    try:
        response = model.generate_content([system_instruction, context_prompt, *uploaded_files])
        return response.text # Return raw text, we will parse JSON in the app
    except Exception as e:
        return {"error": str(e)}

def create_word_doc(diary_df, ta_df, da_df):
    """Generates the A3 Word Document with all 3 tables."""
    doc = Document()
    
    # Set Page Size to A3 (297mm x 420mm)
    section = doc.sections[0]
    section.page_width = Mm(297)
    section.page_height = Mm(420)
    
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(11)

    # 1. Tour Diary Table
    doc.add_heading('1. Tour Diary (Arrival/Dispatch)', level=1)
    if not diary_df.empty:
        t = doc.add_table(rows=1, cols=len(diary_df.columns))
        t.style = 'Table Grid'
        hdr_cells = t.rows[0].cells
        for i, col in enumerate(diary_df.columns):
            hdr_cells[i].text = str(col)
        for _, row in diary_df.iterrows():
            row_cells = t.add_row().cells
            for i, item in enumerate(row):
                row_cells[i].text = str(item)

    doc.add_paragraph("\n")

    # 2. TA Calculation Table
    doc.add_heading('2. TA Calculation (Tickets/Fares)', level=1)
    if not ta_df.empty:
        t = doc.add_table(rows=1, cols=len(ta_df.columns))
        t.style = 'Table Grid'
        hdr_cells = t.rows[0].cells
        for i, col in enumerate(ta_df.columns):
            hdr_cells[i].text = str(col)
        for _, row in ta_df.iterrows():
            row_cells = t.add_row().cells
            for i, item in enumerate(row):
                row_cells[i].text = str(item)

    doc.add_paragraph("\n")

    # 3. DA Calculation Table
    doc.add_heading('3. DA Calculation (Daily Allowance)', level=1)
    if not da_df.empty:
        t = doc.add_table(rows=1, cols=len(da_df.columns))
        t.style = 'Table Grid'
        hdr_cells = t.rows[0].cells
        for i, col in enumerate(da_df.columns):
            hdr_cells[i].text = str(col)
        for _, row in da_df.iterrows():
            row_cells = t.add_row().cells
            for i, item in enumerate(row):
                row_cells[i].text = str(item)

    return doc
