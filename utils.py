import os
import glob
import time
import google.generativeai as genai
from docx import Document
from docx.shared import Mm, Pt

# Directory for permanent rules
RULES_DIR = "rules_storage"
if not os.path.exists(RULES_DIR):
    os.makedirs(RULES_DIR)

def save_permanent_rule(uploaded_file):
    """Saves a rule file (PDF) permanently to disk."""
    if uploaded_file is not None:
        file_path = os.path.join(RULES_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

def list_saved_rules():
    """Lists all saved rule files."""
    return [os.path.basename(x) for x in glob.glob(os.path.join(RULES_DIR, "*.pdf"))]

def call_gemini_extraction(api_key, trip_files, context_prompt):
    """
    1. Uploads Saved Rules (Statutes).
    2. Uploads Current Trip Docs.
    3. Uses gemini-3-pro-preview to calculate based on the Rules.
    """
    if not api_key:
        return {"error": "No API Key provided"}

    genai.configure(api_key=api_key)
    
    # 1. Gather all files to send to AI
    gemini_files = []
    
    # A. Upload PERMANENT RULES (The Statutes/Circulars)
    rule_paths = glob.glob(os.path.join(RULES_DIR, "*.pdf"))
    for path in rule_paths:
        print(f"Uploading Rule: {path}")
        g_file = genai.upload_file(path)
        gemini_files.append(g_file)

    # B. Upload CURRENT TRIP FILES (Diary, Salary Slip)
    for f in trip_files:
        # Save temp file
        with open(f.name, "wb") as temp_f:
            temp_f.write(f.getbuffer())
        # Upload to Gemini
        g_file = genai.upload_file(f.name)
        gemini_files.append(g_file)

    # Wait for files to process (important for large PDFs)
    # In a production app, you might want a loop to check .state == 'ACTIVE'
    time.sleep(2) 

    # 2. The "High Intelligence" Prompt
    system_instruction = """
    You are an expert University Auditor and Accountant.
    
    **YOUR GOAL:** Calculate TA (Travel Allowance) and DA (Daily Allowance) for the user based strictly on the provided 'Rule Documents' and 'Statutes'.

    **STEP 1: IDENTIFY USER**
    - Look at the 'Salary Slip' or 'Pay Slip'.
    - Extract: Name, Designation, Pay Level (e.g., Level 14, 13A), and Basic Pay.
    - These determine the user's entitlement rates in the Rules.

    **STEP 2: ANALYZE RULES (Crucial)**
    - Scan the uploaded 'Rule Documents' (PDFs) for the TA/DA rates corresponding to the user's Pay Level.
    - Specifically look for 'Daily Allowance' rules:
        - Does the rule say DA is calculated on a 24-hour block or Calendar Day?
        - How is 'Absence from Headquarter' defined?
        - Is travel time included in DA calculation? (Usually, yes, from Dispatch to Arrival).
        - What are the rates for 'Hotel/Stay' vs 'Food/Ordinary' DA?

    **STEP 3: EXTRACT TRIP DATA**
    - From the 'Tour Diary', extract every journey.
    - Columns: Dispatch Date/Time, Arrival Date/Time, Mode, Purpose.

    **STEP 4: PERFORM CALCULATIONS**
    - **TA:** Calculate Fare based on class of travel allowed for this Pay Level.
    - **DA:** Calculate the *exact duration* (hours/days) user was outside headquarters (From Dispatch Time to Return Arrival Time).
    - Apply the rule: 
        - < 6 hours: 30% or 0.5 DA? (Check Rule)
        - 6-12 hours: 50% or 0.7 DA? (Check Rule)
        - > 12 hours: 100% DA? (Check Rule)
    
    **OUTPUT FORMAT (JSON ONLY):**
    {
      "user_details": {
        "name": "...",
        "designation": "...",
        "pay_level": "...",
        "rule_used": "Name of rule/circular found"
      },
      "tour_diary": [
        {
          "Dispatch_Station": "...", "Dispatch_Date": "...", "Dispatch_Hour": "...",
          "Arrival_Station": "...", "Arrival_Date": "...", "Arrival_Hour": "...",
          "Mode_of_Travel": "...", "Purpose": "..."
        }
      ],
      "ta_data": [
         {"Mode": "...", "Ticket_No": "...", "Fare_Amount": "...", "Remark": "..."}
      ],
      "da_calculation": [
        {
           "Date": "...", 
           "Start_Time": "...", 
           "End_Time": "...", 
           "Duration_Hours": "...",
           "Rate_Applied": "...",
           "DA_Amount": "..."
        }
      ]
    }
    """

    # Use 1.5 Pro for complex reasoning (Rules + Math)
    model = genai.GenerativeModel(model_name="gemini-3-pro-preview")

    try:
        response = model.generate_content([system_instruction, context_prompt, *gemini_files])
        return response.text
    except Exception as e:
        return {"error": str(e)}

def create_word_doc(diary_df, ta_df, da_df):
    """Generates the A3 Word Document."""
    doc = Document()
    
    # Set Page Size to A3
    section = doc.sections[0]
    section.page_width = Mm(297)
    section.page_height = Mm(420)
    
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(11)

    doc.add_heading('University TA/DA Claim Form', 0)

    # 1. Tour Diary
    doc.add_heading('1. Tour Diary (Movement)', level=1)
    if not diary_df.empty:
        t = doc.add_table(rows=1, cols=len(diary_df.columns))
        t.style = 'Table Grid'
        hdr = t.rows[0].cells
        for i, col in enumerate(diary_df.columns):
            hdr[i].text = str(col)
        for _, row in diary_df.iterrows():
            row_cells = t.add_row().cells
            for i, item in enumerate(row):
                row_cells[i].text = str(item)

    doc.add_paragraph("\n")

    # 2. TA Table
    doc.add_heading('2. TA Calculation (Fares)', level=1)
    if not ta_df.empty:
        t = doc.add_table(rows=1, cols=len(ta_df.columns))
        t.style = 'Table Grid'
        hdr = t.rows[0].cells
        for i, col in enumerate(ta_df.columns):
            hdr[i].text = str(col)
        for _, row in ta_df.iterrows():
            row_cells = t.add_row().cells
            for i, item in enumerate(row):
                row_cells[i].text = str(item)

    doc.add_paragraph("\n")

    # 3. DA Table
    doc.add_heading('3. DA Calculation (Duration Based)', level=1)
    if not da_df.empty:
        t = doc.add_table(rows=1, cols=len(da_df.columns))
        t.style = 'Table Grid'
        hdr = t.rows[0].cells
        for i, col in enumerate(da_df.columns):
            hdr[i].text = str(col)
        for _, row in da_df.iterrows():
            row_cells = t.add_row().cells
            for i, item in enumerate(row):
                row_cells[i].text = str(item)

    return doc


