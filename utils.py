import os
import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Mm

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

def call_gemini_extraction(api_key, files_content, context_prompt):
    """
    Placeholder for the actual Gemini API call.
    In a real app, you would send the image/pdf bytes to 
    genai.GenerativeModel('gemini-1.5-pro').generate_content(...)
    """
    if not api_key:
        return {"error": "No API Key provided"}
    
    try:
        genai.configure(api_key=api_key)
        # mocked response for demonstration
        return {
            "name": "Dr. Vaibhav Chaudhari",
            "designation": "Associate Professor",
            "pay_scale": "Level 13A",
            "tour_data": [
                {"date": "2025-10-24", "from": "Navsari", "to": "Statue of Unity", "mode": "Car", "distance": 150},
                {"date": "2025-10-26", "from": "Statue of Unity", "to": "Navsari", "mode": "Car", "distance": 150}
            ]
        }
    except Exception as e:
        return {"error": str(e)}

def create_word_doc(data_df):
    """Generates the A3 Word Document."""
    doc = Document()
    
    # Set Page Size to 297mm x 420mm (A3)
    section = doc.sections[0]
    section.page_width = Mm(297)
    section.page_height = Mm(420)
    
    doc.add_heading('TA/DA Calculation Sheet', 0)
    
    # Add table based on DataFrame
    t = doc.add_table(rows=1, cols=len(data_df.columns))
    t.style = 'Table Grid'
    
    # Add headers
    hdr_cells = t.rows[0].cells
    for i, col_name in enumerate(data_df.columns):
        hdr_cells[i].text = str(col_name)
    
    # Add data
    for index, row in data_df.iterrows():
        row_cells = t.add_row().cells
        for i, item in enumerate(row):
            row_cells[i].text = str(item)
            
    return doc