import os
import glob
import time
import pandas as pd
import google.generativeai as genai
import json

# ... (Keep existing RULES_DIR and save_permanent_rule functions unchanged) ...

def call_gemini_extraction(api_key, trip_files, context_prompt):
    """
    Uses gemini-3-flash-preview (or pro) to extract data based on Statutes.
    """
    if not api_key:
        return {"error": "No API Key provided"}

    genai.configure(api_key=api_key)
    
    gemini_files = []
    # ... (Keep existing file upload logic unchanged) ...
    # Upload Trip Files
    for f in trip_files:
        with open(f.name, "wb") as temp_f:
            temp_f.write(f.getbuffer())
        g_file = genai.upload_file(f.name)
        gemini_files.append(g_file)

    time.sleep(2) 

    # --- UPDATED PROMPT TO MATCH YOUR CSV FORMAT ---
    system_instruction = """
    You are a University Accountant.
    Extract the Tour Diary exactly into the following JSON format.
    
    RETURN JSON ONLY.
    
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
          "Mode_of_Travel": "Bus/Rail/Car", 
          "Purpose": "Reason for travel"
        }
      ]
    }
    """
    model = genai.GenerativeModel(model_name="gemini-3-flash-preview") # changed to stable model name
    try:
        response = model.generate_content([system_instruction, context_prompt, *gemini_files])
        return response.text
    except Exception as e:
        return {"error": str(e)}

# ... (Keep create_complex_claim_form unchanged for now) ...

