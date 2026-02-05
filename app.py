import streamlit as st
import google.generativeai as genai
import pandas as pd
from docx import Document
from docx.shared import Mm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from datetime import datetime
import json
import io

# --- Page Config ---
st.set_page_config(page_title="NAU Smart Tour Diary", layout="wide")

# --- API Configuration ---
st.sidebar.header("Settings")
api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    # Using gemini-1.5-flash for speed and reliability in extraction
    model = genai.GenerativeModel('gemini-1.5-flash')

# --- Calculation Logic (Rules & Regulations) ---
def calculate_da(total_hours):
    """
    Applies standard Government/NAU rules:
    - Less than 6 hours: 30% DA
    - 6 to 12 hours: 50% DA
    - More than 12 hours: 100% DA
    (Calculated per 24-hour block or fraction thereof)
    """
    days = int(total_hours // 24)
    remaining = total_hours % 24
    
    da_multiplier = float(days)
    if remaining >= 12:
        da_multiplier += 1.0
    elif remaining >= 6:
        da_multiplier += 0.5
    else:
        da_multiplier += 0.3
        
    return da_multiplier

# --- AI Extraction Prompt ---
SYSTEM_PROMPT = """
You are an expert administrative assistant at Navsari Agricultural University (NAU). 
Your task is to extract tour details from the provided text/image and return ONLY a JSON object.
Rules for extraction:
1. Identify every leg of the journey (Departure Station, Date, Time, Arrival Station, Date, Time).
2. Identify the Mode of Journey (Bus, Train, Taxi).
3. Identify Fare and Ticket Numbers.
4. If a return to 'Navsari' or 'HQ' is mentioned, mark it as the end of that tour leg.

Format the output exactly like this:
{
  "journey": [
    {
      "dep_stn": "Station Name",
      "dep_dt": "YYYY-MM-DD",
      "dep_tm": "HH:MM",
      "arr_stn": "Station Name",
      "arr_dt": "YYYY-MM-DD",
      "arr_tm": "HH:MM",
      "mode": "Mode",
      "ticket": "TicketNo",
      "fare": 0.0,
      "remarks": "Purpose"
    }
  ]
}
"""

# --- Streamlit UI ---
st.title("🚀 NAU Smart Tour Diary Automation")

tab1, tab2 = st.tabs(["Data Extraction", "Final Report"])

with tab1:
    user_input = st.text_area("Paste Tour Details or Bill Description here:", height=200, 
                             placeholder="Ex: Departed Navsari on 05/02/2026 at 08:00 AM by Bus to Surat for meeting. Returned to Navsari at 09:00 PM same day. Fare 150/-")
    
    if st.button("Extract Data with Gemini"):
        if not api_key:
            st.error("Please enter your API Key in the sidebar.")
        else:
            with st.spinner("Gemini is analyzing rules and extracting data..."):
                response = model.generate_content(f"{SYSTEM_PROMPT}\n\nUser Input: {user_input}")
                try:
                    # Clean the response to ensure it's valid JSON
                    json_str = response.text.replace("```json", "").replace("```", "").strip()
                    data = json.loads(json_str)
                    df = pd.DataFrame(data['journey'])
                    st.session_state['journey_data'] = df
                    st.success("Data extracted successfully!")
                except Exception as e:
                    st.error(f"Error parsing data: {e}")
                    st.write("Raw Response:", response.text)

    if 'journey_data' in st.session_state:
        edited_df = st.data_editor(st.session_state['journey_data'], num_rows="dynamic")
        st.session_state['journey_data'] = edited_df

with tab2:
    if 'journey_data' in st.session_state:
        st.subheader("DA Calculation & Summary")
        
        # Salary/Rate Inputs
        col1, col2 = st.columns(2)
        with col1:
            da_rate = st.number_input("Your Daily Allowance (DA) Rate (Rs.)", value=1000)
        with col2:
            name = st.text_input("Name", value="Dr. Vaibhavkumar Chaudhari")
            
        # Perform calculation based on rules
        df = st.session_state['journey_data']
        try:
            # Simple calculation for the whole trip duration
            start = datetime.strptime(f"{df.iloc[0]['dep_dt']} {df.iloc[0]['dep_tm']}", "%Y-%m-%d %H:%M")
            end = datetime.strptime(f"{df.iloc[-1]['arr_dt']} {df.iloc[-1]['arr_tm']}", "%Y-%m-%d %H:%M")
            
            diff = end - start
            total_hours = diff.total_seconds() / 3600
            da_days = calculate_da(total_hours)
            total_da = da_days * da_rate
            total_fare = df['fare'].astype(float).sum()
            
            st.info(f"Total Absence: {total_hours:.2f} hours | DA Factor: {da_days} | Total: ₹{total_da + total_fare}")
            
            # Export Logic (Simplified for brevity)
            if st.button("Generate Docx Report"):
                doc = Document()
                doc.add_heading('NAU Tour Bill', 0)
                doc.add_paragraph(f"Name: {name}")
                doc.add_paragraph(f"Total DA: {total_da} (based on {da_days} days)")
                doc.add_paragraph(f"Total Fare: {total_fare}")
                
                # Add Table
                table = doc.add_table(rows=1, cols=4)
                table.style = 'Table Grid'
                hdr_cells = table.rows[0].cells
                hdr_cells[0].text = 'Date'
                hdr_cells[1].text = 'Journey'
                hdr_cells[2].text = 'Fare'
                hdr_cells[3].text = 'Remarks'
                
                for _, row in df.iterrows():
                    row_cells = table.add_row().cells
                    row_cells[0].text = row['dep_dt']
                    row_cells[1].text = f"{row['dep_stn']} to {row['arr_stn']}"
                    row_cells[2].text = str(row['fare'])
                    row_cells[3].text = row['remarks']

                buffer = io.BytesIO()
                doc.save(buffer)
                st.download_button("Download Bill", buffer.getvalue(), "Tour_Bill.docx")
                
        except Exception as e:
            st.warning("Please ensure dates and times are correctly formatted in the table.")
