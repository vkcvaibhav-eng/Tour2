import streamlit as st
import pandas as pd
import json
from datetime import datetime, time

st.set_page_config(layout="wide", page_title="Edit Tour Diary")
st.title("🗓️ Edit Tour Diary (Schedule)")

if 'extracted_data' not in st.session_state:
    st.warning("No data found. Please go to 'Upload & Extract' first.")
    st.stop()

# --- Helper Functions for Data Cleaning ---
def parse_time_safe(t):
    """Converts various string time formats to datetime.time objects."""
    if pd.isna(t) or t == "":
        return None
    try:
        # Try converting strictly from string
        return pd.to_datetime(str(t), format='%H:%M').time()
    except:
        return None

# --- 1. Load & Process Data ---
if 'raw_diary_df' not in st.session_state:
    raw_response = st.session_state['extracted_data']
    
    # Robust JSON Parsing
    try:
        if isinstance(raw_response, dict):
            data = raw_response
        else:
            text_data = raw_response
            if "```json" in text_data:
                text_data = text_data.split("```json")[1].split("```")[0]
            elif "```" in text_data:
                text_data = text_data.split("```")[1].split("```")[0]
            data = json.loads(text_data)
            
        diary_data = data.get("tour_diary", [])
        
    except Exception as e:
        st.error(f"Error reading data: {e}")
        diary_data = [] # Fallback to empty list so app doesn't crash

    # Desired Columns
    desired_order = [
        "Departure_Date", "Departure_Time", "Departure_Place",
        "Arrival_Date", "Arrival_Time", "Arrival_Place",
        "Mode_of_Travel", "Purpose"
    ]
    
    # Create DataFrame
    df = pd.DataFrame(diary_data)
    
    # Ensure all columns exist
    for col in desired_order:
        if col not in df.columns:
            df[col] = None  # Use None instead of "" for safety
            
    # Reorder
    df = df[desired_order]

    # --- CRITICAL FIX: Convert Types for Streamlit Editor ---
    # 1. Convert Dates (Handle DD-MM-YYYY)
    for col in ["Departure_Date", "Arrival_Date"]:
        df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

    # 2. Convert Times (Handle HH:MM strings)
    for col in ["Departure_Time", "Arrival_Time"]:
        df[col] = df[col].apply(parse_time_safe)

    st.session_state['raw_diary_df'] = df

# --- 2. Buttons to Add Rows ---
col_add, col_stay = st.columns([1, 5])
with col_add:
    # "num_rows='dynamic'" inside the editor handles manual adds, 
    # but sometimes a dedicated button is helpful if the table is empty.
    if st.button("➕ Add New Row"):
        new_row = pd.DataFrame([{col: None for col in st.session_state['raw_diary_df'].columns}])
        st.session_state['raw_diary_df'] = pd.concat([st.session_state['raw_diary_df'], new_row], ignore_index=True)
        st.rerun()

with col_stay:
    if st.button("🏨 Add 'Stay' Row"):
        # Adds a row pre-filled with "Stay" in purpose
        new_row = pd.DataFrame([{
            "Departure_Date": None, "Departure_Time": None, "Departure_Place": "Hotel/Guest House",
            "Arrival_Date": None, "Arrival_Time": None, "Arrival_Place": "Same",
            "Mode_of_Travel": "Bus", "Purpose": "Stay"
        }])
        st.session_state['raw_diary_df'] = pd.concat([st.session_state['raw_diary_df'], new_row], ignore_index=True)
        st.rerun()

# --- 3. The Editable Table ---
st.info("Step 1: Verify the schedule below. Use the **+** icon at the bottom of the table to add more rows.")

try:
    edited_diary = st.data_editor(
        st.session_state['raw_diary_df'],
        num_rows="dynamic",  # Allows manual adding/deleting rows
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
                required=False
            ),
            "Purpose": st.column_config.TextColumn("Purpose")
        }
    )
    
    # Sync edits back to session state immediately
    st.session_state['raw_diary_df'] = edited_diary

except Exception as e:
    st.error(f"Data Error: {e}")
    st.write("Raw data for debugging:", st.session_state['raw_diary_df'])

st.markdown("---")

# --- 4. Save & Proceed ---
col1, col2 = st.columns([3, 1])
with col1:
    st.caption("Review the dates and places above. Once correct, proceed to calculate money.")
with col2:
    if st.button("✅ Confirm & Go to Calc"):
        st.session_state['final_tour_diary'] = edited_diary
        st.switch_page("pages/4_🧮_TA_DA_Calc.py")
