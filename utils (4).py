import os
import glob
import time
import pandas as pd
import google.generativeai as genai
import json

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
    Uses gemini-3-flash-preview to extract data.
    """
    if not api_key:
        return {"error": "No API Key provided"}

    genai.configure(api_key=api_key)
    
    gemini_files = []
    
    # --- 1. Upload Rules/Statutes (Context) ---
    rule_files = glob.glob(os.path.join(RULES_DIR, "*.pdf"))
    for rule_path in rule_files:
        g_file = genai.upload_file(rule_path)
        gemini_files.append(g_file)

    # --- 2. Upload Trip Files (Documents) ---
    for f in trip_files:
        # Check if it's a file path string or a Streamlit object
        if isinstance(f, str):
            if os.path.exists(f):
                g_file = genai.upload_file(f)
                gemini_files.append(g_file)
        else:
            with open(f.name, "wb") as temp_f:
                temp_f.write(f.getbuffer())
            g_file = genai.upload_file(f.name)
            gemini_files.append(g_file)

    time.sleep(2) 

    # --- UPDATED PROMPT: FORCE KM EXTRACTION ---
    system_instruction = """
    You are a University Accountant.
    Extract the Tour Diary from the uploaded documents exactly into JSON.
    
    CRITICAL INSTRUCTIONS:
    1. EXTRACT 'KM' (Kilometers): If the diary table has a 'KM', 'Distance', or 'Kms' column, you MUST extract that number for the specific row.
    2. MODE OF TRAVEL: Detect 'Private Vehicle', 'University Vehicle', 'Bus', 'Rail', etc.
    3. PRIVATE VEHICLE RATE: If a 'Fare Enquiry' document is provided showing a bus rate, try to extract that rate into 'Ticket_Price'.
    
    JSON Structure:
    {
      "tour_diary": [
        {
          "Departure_Date": "DD-MM-YYYY", 
          "Departure_Time": "HH:MM (24hr)", 
          "Departure_Place": "City/Station Name", 
          "Arrival_Date": "DD-MM-YYYY", 
          "Arrival_Time": "HH:MM (24hr)", 
          "Arrival_Place": "City/Station Name", 
          "Mode_of_Travel": "Bus/Rail/Private Vehicle/University Vehicle (No)/Auto Rickshaw/Flight", 
          "Purpose": "Reason for travel",
          "KM": "Distance in KM (Extract strictly from document)",
          "Ticket_Price": "Ticket Amount (or Bus Fare for Pvt Vehicle)"
        }
      ]
    }
    """

    # --- Call Gemini ---
    model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview",
        generation_config={"response_mime_type": "application/json"},
        system_instruction=system_instruction
    )

    try:
        response = model.generate_content([context_prompt, *gemini_files])
        return response.text
    except Exception as e:
        return {"error": str(e)}

# --- Placeholder for Export Function ---
from docx import Document
def create_complex_claim_form(diary, ta, da):
    doc = Document()
    doc.add_heading('TA/DA Claim Form', 0)
    doc.add_paragraph('Automated Export Placeholder')
    return doc
