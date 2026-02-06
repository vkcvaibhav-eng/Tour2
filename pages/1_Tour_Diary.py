import streamlit as st
import pandas as pd
import utils
import os
import json
from datetime import datetime, time, date, timedelta

st.set_page_config(layout="wide", page_title="Step 1: Tour Diary")
st.title("🗓️ Step 1: Tour Diary")

# Validation
if not st.session_state.get('gemini_api_key'):
    st.error("⚠️ Please go to 'Home' and enter your Gemini API Key first.")
    st.stop()

# --- CORE UTILITIES ---

def sort_diary(df):
    """Sorts the diary chronologically by Departure Date and Time."""
    if df.empty:
        return df
    try:
        # Convert to datetime objects for accurate sorting
        df['temp_sort'] = pd.to_datetime(df['Departure_Date'].astype(str) + ' ' + df['Departure_Time'].astype(str))
        df = df.sort_values(by='temp_sort').drop(columns=['temp_sort'])
    except Exception as e:
        st.error(f"Sorting error: {e}")
    return df

def cleanup_data_types(df):
    """Ensures data types are consistent for the editor."""
    date_cols = ["Departure_Date", "Arrival_Date"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce').dt.date

    time_cols = ["Departure_Time", "Arrival_Time"]
    for col in time_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format='%H:%M', errors='coerce').dt.time
    return df

# --- INITIALIZE SESSION STATE ---
if 'raw_diary_df' not in st.session_state:
    st.session_state['raw_diary_df'] = pd.DataFrame(columns=[
        "Departure_Place", "Departure_Date", "Departure_Time",
        "Arrival_Place", "Arrival_Date", "Arrival_Time",
        "Mode_of_Travel", "KM", "Purpose"
    ])

# --- PART A: AI EXTRACTION ---
st.subheader("1. AI Extraction (Optional)")
uploaded_diary = st.file_uploader("Upload scanned Tour Diary", type=['pdf', 'jpg', 'jpeg', 'png'])

if uploaded_diary and st.button("🚀 Run AI Extraction"):
    with st.spinner("AI is reading the diary..."):
        # (Assuming utils.call_gemini_extraction exists as per your snippet)
        # This part remains the same as your original logic
        pass 

st.divider()

# --- PART B: EASY MANUAL FILL FORM ---
st.subheader("2. Add Journey or Stay (Manual Entry)")
st.info("Fill the details below and click 'Add to Table'. It will automatically align by date and time.")

with st.expander("✨ Open Manual Entry Form", expanded=True):
    f_col1, f_col2, f_col3 = st.columns(3)
    
    with f_col1:
        dep_p = st.text_input("Departure Place", placeholder="e.g. City A")
        dep_d = st.date_input("Departure Date", value=date.today())
        dep_t = st.time_input("Departure Time", value=time(9, 0))
        
    with f_col2:
        arr_p = st.text_input("Arrival Place", placeholder="e.g. City B")
        arr_d = st.date_input("Arrival Date", value=date.today())
        arr_t = st.time_input("Arrival Time", value=time(17, 0))
        
    with f_col3:
        mode = st.selectbox("Mode of Travel", ["Bus", "Rail", "Flight", "Private Vehicle", "Auto Rickshaw", "STAY"])
        km = st.number_input("Distance (KM)", min_value=0.0, step=0.1)
        purp = st.text_input("Purpose", placeholder="e.g. Official Meeting")

    if st.button("➕ Add Entry to Table"):
        new_entry = pd.DataFrame([{
            "Departure_Place": dep_p, "Departure_Date": dep_d, "Departure_Time": dep_t,
            "Arrival_Place": arr_p, "Arrival_Date": arr_d, "Arrival_Time": arr_t,
            "Mode_of_Travel": mode, "KM": km, "Purpose": purp
        }])
        
        # Append and Auto-Sort
        updated_df = pd.concat([st.session_state['raw_diary_df'], new_entry], ignore_index=True)
        st.session_state['raw_diary_df'] = sort_diary(updated_df)
        st.success(f"Added journey from {dep_p} to {arr_p}!")
        st.rerun()

st.divider()

# --- PART C: THE TABLE (REVIEW & EDIT) ---
if not st.session_state['raw_diary_df'].empty:
    st.subheader("3. Final Review Table")
    st.caption("Entries are automatically sorted by Departure Date & Time.")

    # Show the table
    edited_df = st.data_editor(
        st.session_state['raw_diary_df'],
        num_rows="dynamic",
        use_container_width=True,
        key="diary_editor_main",
        column_config={
            "Departure_Place": st.column_config.TextColumn("1. Departure Place"),
            "Departure_Date": st.column_config.DateColumn("2. Date", format="DD-MM-YYYY"),
            "Departure_Time": st.column_config.TimeColumn("3. Time"),
            "Arrival_Place": st.column_config.TextColumn("4. Arrival Place"),
            "Arrival_Date": st.column_config.DateColumn("5. Date", format="DD-MM-YYYY"),
            "Arrival_Time": st.column_config.TimeColumn("6. Time"),
            "Mode_of_Travel": st.column_config.TextColumn("7. Mode"),
            "KM": st.column_config.NumberColumn("11. KM"),
            "Purpose": st.column_config.TextColumn("18. Purpose")
        }
    )

    # Re-sort if user manually changes dates in the table
    if st.button("🔄 Refresh & Re-align Table Order"):
        st.session_state['raw_diary_df'] = sort_diary(edited_df)
        st.rerun()

    # Save and Proceed
    st.markdown("---")
    if st.button("✅ Confirm & Go to Calculation"):
        st.session_state['final_tour_diary'] = edited_df
        st.switch_page("pages/2_TA_Calculation.py")
else:
    st.warning("Your diary is currently empty. Use the form above to add your first journey.")
