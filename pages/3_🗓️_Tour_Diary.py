import streamlit as st
import pandas as pd
import json
from datetime import datetime, time

st.set_page_config(layout="wide", page_title="Edit Tour Diary")
st.title("🗓️ Edit Tour Diary (Schedule)")

if 'extracted_data' not in st.session_state:
    st.warning("No data found. Please go to 'Upload & Extract' first.")
    st.stop()

# --- HELPER: Time Parsing & Sorting ---
def parse_time_safe(t):
    if pd.isna(t) or t == "" or t is None:
        return None
    try:
        if isinstance(t, str):
            return pd.to_datetime(t, format='%H:%M').time()
        return t
    except:
        return None

def sort_diary(df):
    """Sorts the diary chronologically by Departure Date and Time."""
    try:
        df['temp_sort'] = df.apply(
            lambda x: datetime.combine(x['Departure_Date'], x['Departure_Time']) 
            if pd.notnull(x['Departure_Date']) and pd.notnull(x['Departure_Time']) 
            else pd.NaT, axis=1
        )
        df = df.sort_values(by='temp_sort').drop(columns=['temp_sort'])
    except:
        pass
    return df

# --- 1. LOAD DATA ---
if 'raw_diary_df' not in st.session_state:
    raw_response = st.session_state['extracted_data']
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
    except:
        diary_data = []

    # --- UPDATED COLUMN ORDER (Your Request) ---
    desired_order = [
        "Departure_Place", "Departure_Date", "Departure_Time", 
        "Arrival_Place", "Arrival_Date", "Arrival_Time", 
        "Mode_of_Travel", "Purpose"
    ]
    
    df = pd.DataFrame(diary_data)
    for col in desired_order:
        if col not in df.columns:
            df[col] = None
    
    # Type Conversion
    for col in ["Departure_Date", "Arrival_Date"]:
        df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
    for col in ["Departure_Time", "Arrival_Time"]:
        df[col] = df[col].apply(parse_time_safe)

    st.session_state['raw_diary_df'] = df[desired_order]

# Ensure types are correct every reload
st.session_state['raw_diary_df']["Departure_Date"] = pd.to_datetime(st.session_state['raw_diary_df']["Departure_Date"])
st.session_state['raw_diary_df']["Arrival_Date"] = pd.to_datetime(st.session_state['raw_diary_df']["Arrival_Date"])


# ==========================================
# SECTION: EASY ADD ENTRY (Updated Order)
# ==========================================
st.markdown("### ➕ Add Details Easily")
tab_travel, tab_stay = st.tabs(["🚌 Add Journey (Travel)", "🏨 Add Stay (Halt)"])

# --- TAB 1: ADD TRAVEL ---
with tab_travel:
    with st.form("add_travel_form", clear_on_submit=True):
        # Row 1: Departure
        c1, c2, c3 = st.columns(3)
        dep_place = c1.text_input("1. Departure Place")
        dep_date = c2.date_input("2. Departure Date")
        dep_time = c3.time_input("3. Departure Time", value=None)
        
        # Row 2: Arrival
        c4, c5, c6 = st.columns(3)
        arr_place = c4.text_input("4. Arrival Place")
        arr_date = c5.date_input("5. Arrival Date")
        arr_time = c6.time_input("6. Arrival Time", value=None)
        
        # Row 3: Mode & Purpose
        c7, c8 = st.columns([1, 2])
        mode = c7.text_input("7. Mode (e.g. Uni Vehicle (GJ-21-1234))")
        purpose = c8.text_input("8. Purpose of Journey", value="Official Work")

        if st.form_submit_button("Add Journey"):
            new_row = {
                "Departure_Place": dep_place,
                "Departure_Date": pd.to_datetime(dep_date),
                "Departure_Time": dep_time,
                "Arrival_Place": arr_place,
                "Arrival_Date": pd.to_datetime(arr_date),
                "Arrival_Time": arr_time,
                "Mode_of_Travel": mode,
                "Purpose": purpose
            }
            st.session_state['raw_diary_df'] = pd.concat([st.session_state['raw_diary_df'], pd.DataFrame([new_row])], ignore_index=True)
            st.session_state['raw_diary_df'] = sort_diary(st.session_state['raw_diary_df'])
            st.rerun()

# --- TAB 2: ADD STAY ---
with tab_stay:
    st.caption("Use this to record a night halt.")
    with st.form("add_stay_form", clear_on_submit=True):
        s1, s2, s3 = st.columns(3)
        stay_place = s1.text_input("Place of Stay")
        stay_date_in = s2.date_input("Check-in Date")
        stay_time_in = s3.time_input("Check-in Time", value=time(20, 0))
        
        s4, s5, s6 = st.columns(3)
        stay_remark = s4.text_input("Remark", value="Night Halt")
        stay_date_out = s5.date_input("Check-out Date")
        stay_time_out = s6.time_input("Check-out Time", value=time(8, 0))

        if st.form_submit_button("Add Stay Record"):
            new_row = {
                "Departure_Place": stay_place,
                "Departure_Date": pd.to_datetime(stay_date_in),
                "Departure_Time": stay_time_in,
                "Arrival_Place": stay_place,
                "Arrival_Date": pd.to_datetime(stay_date_out),
                "Arrival_Time": stay_time_out,
                "Mode_of_Travel": "None",
                "Purpose": stay_remark
            }
            st.session_state['raw_diary_df'] = pd.concat([st.session_state['raw_diary_df'], pd.DataFrame([new_row])], ignore_index=True)
            st.session_state['raw_diary_df'] = sort_diary(st.session_state['raw_diary_df'])
            st.rerun()

st.markdown("---")

# ==========================================
# SECTION: VIEW & EDIT TABLE (Specific Order)
# ==========================================
st.info("👇 **Review Your Schedule**")

# Reorder Dataframe just to be safe before showing
st.session_state['raw_diary_df'] = st.session_state['raw_diary_df'][[
    "Departure_Place", "Departure_Date", "Departure_Time", 
    "Arrival_Place", "Arrival_Date", "Arrival_Time", 
    "Mode_of_Travel", "Purpose"
]]

edited_diary = st.data_editor(
    st.session_state['raw_diary_df'],
    num_rows="dynamic",
    use_container_width=True,
    key="diary_editor",
    column_config={
        "Departure_Place": st.column_config.TextColumn("1. From Place"),
        "Departure_Date": st.column_config.DateColumn("2. Dep Date", format="DD-MM-YYYY"),
        "Departure_Time": st.column_config.TimeColumn("3. Dep Time", format="HH:mm"),
        
        "Arrival_Place": st.column_config.TextColumn("4. To Place"),
        "Arrival_Date": st.column_config.DateColumn("5. Arr Date", format="DD-MM-YYYY"),
        "Arrival_Time": st.column_config.TimeColumn("6. Arr Time", format="HH:mm"),
        
        "Mode_of_Travel": st.column_config.TextColumn(
            "7. Mode (Detailed)", 
            help="Type details like: 'University Vehicle (GJ-21-1234)' or 'Private Car'"
        ),
        "Purpose": st.column_config.TextColumn("8. Purpose")
    }
)

# Sync edits
st.session_state['raw_diary_df'] = edited_diary

st.markdown("---")
col1, col2 = st.columns([3, 1])
with col1:
    st.caption("Once the list above is correct, proceed to calculation.")
with col2:
    if st.button("✅ Confirm & Go to Calc"):
        st.session_state['final_tour_diary'] = edited_diary
        st.switch_page("pages/4_🧮_TA_Calculation.py")
