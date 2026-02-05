import streamlit as st
import google.generativeai as genai
import pandas as pd
from docx import Document
from docx.shared import Mm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import io
import json
import tempfile
import os

# --- Page Configuration ---
st.set_page_config(page_title="NAU Tour Diary Automation", layout="wide")

# --- Sidebar: Setup ---
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")
model_choice = st.sidebar.selectbox(
    "Select Model", 
    ["gemini-3-pro-preview", "gemini-3-flash-preview"],
    index=0,
    help="Pro is better for complex reasoning; Flash is faster."
)

# --- Definitions & Rules (Hardcoded from your prompt) ---
RULES_CONTEXT = """
**Definitions & Calculation Rules for TA/DA:**

1. **Mode of Transport:** Actual means of conveyance (Railway, Public Bus, Air).
2. **Class of Travel:** Entitlement (I / II / III) based on pay level/designation.
3. **Ticket Price:** Actual fare paid. If lost, official fare enquiry rate is used.
4. **Road Travel by Other Vehicle:** Includes State Transport Bus, Metro, Auto, Taxi.
   * *Critical Rule:* Use of private vehicle is NOT ordinarily admissible. Reimbursement is restricted to the official fare of eligible public transport for the same route, NOT mileage.
5. **Days of Daily Allowance:** Based on total duration of absence (departure to arrival) calculated per University rules.
6. **Daily Allowance Rate:** Fixed rate based on Pay Level and City Classification.

**Task:**
Analyze the uploaded Salary Slip, Tour Diary Draft, and Tickets/Bills.
Extract a JSON list of journey segments. For each segment, calculate the receivable amount based on the rules above.
If a private vehicle was used, find the equivalent public transport fare (or estimate it based on standard rates if not explicitly found) and mark it in the notes.
"""

def generate_tour_diary_docx(data_df):
    """Generates the Word document with A3 dimensions (297mm x 420mm)."""
    doc = Document()
    
    # Set Page Size to A3 (297mm x 420mm)
    section = doc.sections[0]
    section.page_width = Mm(297)
    section.page_height = Mm(420)
    section.left_margin = Mm(15)
    section.right_margin = Mm(15)
    section.top_margin = Mm(15)
    section.bottom_margin = Mm(15)

    # Title
    head = doc.add_heading('TOUR DIARY / TRAVEL ALLOWANCE BILL', 0)
    head.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Table Creation (17 Columns matching the PDF structure)
    # Col 1: Sr. No, 2: Place (Dep), 3: Date, 4: Time, 5: Place (Arr), 6: Date, 7: Time
    # 8: Mode, 9: Class, 10: Ticket Price, 11: Total Amount, 12: Road Travel Details
    # 13: Days of DA, 14: DA Rate, 15: DA Amount, 16: Total (10+13+16) [Note: PDF says 10+13+16, likely means Ticket+Road+DA]
    # 17: Purpose/Notes
    
    table = doc.add_table(rows=1, cols=17)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Header Row
    hdr_cells = table.rows[0].cells
    headers = [
        "Sr. No.", "Dep. Place", "Dep. Date", "Dep. Time", 
        "Arr. Place", "Arr. Date", "Arr. Time", 
        "Mode", "Class", "Ticket (Rs)", "Total Ticket", 
        "Road Travel Details", "DA Days", "DA Rate", "DA Amount", 
        "Grand Total", "Purpose/Note"
    ]
    
    for i, text in enumerate(headers):
        hdr_cells[i].text = text
        # Optional: formatting for header font size could go here

    # Fill Data
    total_sum = 0
    for index, row in data_df.iterrows():
        row_cells = table.add_row().cells
        row_cells[0].text = str(index + 1)
        row_cells[1].text = str(row.get('departure_place', ''))
        row_cells[2].text = str(row.get('departure_date', ''))
        row_cells[3].text = str(row.get('departure_time', ''))
        row_cells[4].text = str(row.get('arrival_place', ''))
        row_cells[5].text = str(row.get('arrival_date', ''))
        row_cells[6].text = str(row.get('arrival_time', ''))
        row_cells[7].text = str(row.get('mode', ''))
        row_cells[8].text = str(row.get('class_travel', ''))
        row_cells[9].text = str(row.get('ticket_price', 0))
        row_cells[10].text = str(row.get('total_ticket_amount', 0))
        row_cells[11].text = str(row.get('road_travel_details', ''))
        row_cells[12].text = str(row.get('da_days', 0))
        row_cells[13].text = str(row.get('da_rate', 0))
        row_cells[14].text = str(row.get('da_amount', 0))
        
        # Calculate row total
        try:
            row_total = float(row.get('total_ticket_amount', 0)) + float(row.get('da_amount', 0))
            # Note: Col 16 in prompt formula was (10+13+16). Assuming it means Ticket + Road + DA.
            # Adjust logic here if "Road Travel" has a separate cost column not explicitly in extraction.
        except:
            row_total = 0
            
        row_cells[15].text = str(row_total)
        row_cells[16].text = str(row.get('purpose', ''))
        
        total_sum += row_total

    # Summary Row
    sum_row = table.add_row().cells
    sum_row[0].text = "TOTAL"
    sum_row[15].text = str(total_sum)

    # Save to buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def extract_data_with_gemini(files, api_key, model_name):
    genai.configure(api_key=api_key)
    
    # Upload files to Gemini
    uploaded_files = []
    for file in files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.name.split('.')[-1]}") as tmp:
            tmp.write(file.getvalue())
            tmp_path = tmp.name
        
        uploaded_file = genai.upload_file(tmp_path, mime_type=file.type)
        uploaded_files.append(uploaded_file)
        os.remove(tmp_path) # Clean up local temp

    # Prepare Prompt
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
    You are an administrative assistant for a University. 
    {RULES_CONTEXT}
    
    Analyze the attached documents (Salary Slip, Tickets, Tour Draft).
    Extract the tour details into a JSON list where each item represents a row in the Tour Diary.
    
    The JSON keys MUST be exactly: 
    "departure_place", "departure_date", "departure_time", 
    "arrival_place", "arrival_date", "arrival_time", 
    "mode", "class_travel", "ticket_price", "total_ticket_amount", 
    "road_travel_details", "da_days", "da_rate", "da_amount", "purpose"
    
    IMPORTANT: 
    1. If the user used a private vehicle, set 'ticket_price' to the equivalent public bus fare (estimate if necessary based on distance) and note this in 'road_travel_details'.
    2. 'total_ticket_amount' is usually same as 'ticket_price' unless multiple people/tickets.
    3. Calculate 'da_amount' = 'da_days' * 'da_rate'.
    4. Return ONLY the JSON.
    """
    
    result = model.generate_content(uploaded_files + [prompt])
    
    # Clean up JSON string (remove markdown fences if present)
    text = result.text.strip()
    if text.startswith("```json"):
        text = text[7:-3]
    
    return json.loads(text)

# --- Main UI ---
st.title("University Tour Diary Generator (TA/DA)")
st.markdown("Upload your Salary Slip, Tour details, and Tickets. The AI will calculate TA/DA based on University rules.")

with st.expander("Upload Documents", expanded=True):
    uploaded_files = st.file_uploader(
        "Upload Salary Slip, Tour Draft, Tickets/Bills, Circulars", 
        accept_multiple_files=True,
        type=['pdf', 'jpg', 'jpeg', 'png']
    )

if st.button("Process & Calculate"):
    if not api_key:
        st.error("Please enter your Gemini API Key in the sidebar.")
    elif not uploaded_files:
        st.error("Please upload at least one document.")
    else:
        with st.spinner("Analyzing documents and calculating allowances..."):
            try:
                # Extract Data
                json_data = extract_data_with_gemini(uploaded_files, api_key, model_choice)
                df = pd.DataFrame(json_data)
                
                # Save to session state for editing
                st.session_state['df'] = df
                st.success("Extraction Complete! Review the data below.")
            except Exception as e:
                st.error(f"An error occurred: {e}")

# --- Editable Preview ---
if 'df' in st.session_state:
    st.subheader("Review & Edit Data")
    st.markdown("Edit the calculated values if necessary. The 'Total' will update in the final DOCX.")
    
    # Allow user to edit the dataframe
    edited_df = st.data_editor(st.session_state['df'], num_rows="dynamic")
    
    # Export Section
    st.divider()
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("### Export Final Document")
        st.caption("Generates a .docx file with page size 297mm x 420mm (A3).")
        
    with col2:
        docx_file = generate_tour_diary_docx(edited_df)
        st.download_button(
            label="Download Tour Diary (.docx)",
            data=docx_file,
            file_name="Final_Tour_Diary.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

