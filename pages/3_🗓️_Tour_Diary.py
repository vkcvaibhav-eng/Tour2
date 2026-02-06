import streamlit as st
import pandas as pd
import json
from datetime import datetime

st.set_page_config(layout="wide", page_title="Edit Tour Diary")
st.title("🗓️ Edit Tour Diary (Schedule)")

if 'extracted_data' not in st.session_state:
    st.warning("No data found. Please go to 'Upload & Extract' first.")
    st.stop()

# --- 1. Load Raw Data ---
if 'raw_diary_df' not in st.session_state:
    raw_response = st.session_state['extracted_data']
    
    # Robust JSON Parsing
    try:
        if isinstance(raw_response, dict):
            data = raw_response
        else:
            # Clean string if it contains markdown code blocks
            text_data = raw_response
            if "```json" in text_data:
                text_data = text_data.split("```json")[1].split("```")[0]
            elif "```" in text_data:
                text_data = text_data.split("```")[1].split("```")[0]
            data = json.loads(text_data)
            
        diary_data = data.get("tour_diary", [])
        
    except Exception as e:
        st.error(f"Error reading data: {e}")
        st.stop()

    # --- MATCHING YOUR CSV COLUMNS ---
    # We define the order exactly as you requested
    desired_order = [
        "Departure_Date", "Departure_Time", "Departure_Place",
        "Arrival_Date", "Arrival_Time", "Arrival_Place",
        "Mode_of_Travel", "Purpose"
    ]
    
    # Create DataFrame
    df = pd.DataFrame(diary_data)
    
    # Ensure all columns exist even if AI missed one
    for col in desired_order:
        if col not in df.columns:
            df[col] = ""
            
    # Reorder columns matches your CSV
    st.session_state['raw_diary_df'] = df[desired_order]

# --- 2. The Editable Table ---
st.info("Step 1: Verify the schedule below. This matches your Excel format.")

edited_diary = st.data_editor(
    st.session_state['raw_diary_df'],
    num_rows="dynamic",
    use_container_width=True,
    key="diary_editor",
    column_config={
        "Departure_Date": st.column_config.DateColumn("Departure Date", format="DD-MM-YYYY"),
        "Departure_Time": st.column_config.TimeColumn("Departure Time", format="HH:mm"),
        "Departure_Place": st.column_config.TextColumn("Departure Place"),
        
        "Arrival_Date": st.column_config.DateColumn("Arrival Date", format="DD-MM-YYYY"),
        "Arrival_Time": st.column_config.TimeColumn("Arrival Time", format="HH:mm"),
        "Arrival_Place": st.column_config.TextColumn("Arrival Place"),
        
        "Mode_of_Travel": st.column_config.SelectboxColumn(
            "Mode of Travel", 
            options=["Rail", "Bus", "Govt Vehicle", "Private Car", "Air", "Taxi"],
            required=True
        ),
        "Purpose": st.column_config.TextColumn("Purpose")
    }
)

st.markdown("---")

# --- 3. Save & Proceed ---
col1, col2 = st.columns([3, 1])
with col1:
    st.caption("Review the dates and places above. Once correct, proceed to calculate money.")
with col2:
    if st.button("✅ Confirm & Go to Calc"):
        st.session_state['final_tour_diary'] = edited_diary
        st.switch_page("pages/4_🧮_TA_DA_Calc.py")
