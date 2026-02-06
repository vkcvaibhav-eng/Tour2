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
        # Create a temp column for sorting that combines Date + Time
        df['temp_sort'] = df.apply(
            lambda x: datetime.combine(x['Departure_Date'], x['Departure_Time']) 
            if pd.notnull(x['Departure_Date']) and pd.notnull(x['Departure_Time']) 
            else pd.NaT, axis=1
        )
        df = df.sort_values(by='temp_sort').drop(columns=['temp_sort'])
    except Exception as e:
        pass # If sorting fails (e.g. empty dates), just return as is
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

    desired_order = ["Departure_Date", "Departure_Time", "Departure_Place",
                     "Arrival_Date", "Arrival_Time", "Arrival_Place",
                     "Mode_of_Travel", "Purpose"]
    
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
# SECTION: EASY ADD ENTRY (Tabs)
# ==========================================
st.markdown("### ➕ Add Details Easily")
tab_travel, tab_stay = st.tabs(["🚌 Add Journey (Travel)", "🏨 Add Stay (Halt)"])

# --- TAB 1: ADD TRAVEL ---
with tab_travel:
    with st.form("add_travel_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        dep_date = c1.date_input("Departure Date")
        dep_time = c2.time_input("Departure Time", value=None)
        dep_place = c3.text_input("Departure Place")
        mode = c4.selectbox("Mode", ["Bus", "Rail", "Auto Rickshaw", "Taxi", "Govt Vehicle", "Private Car", "Air"])
        
        c5, c6, c7, c8 = st.columns(4)
        arr_date = c5.date_input("Arrival Date")
        arr_time = c6.time_input("Arrival Time", value=None)
        arr_place = c7.text_input("Arrival Place")
        purpose = c8.text_input("Purpose", value="Official Work")

        if st.form_submit_button("Add Journey"):
            new_row = {
                "Departure_Date": pd.to_datetime(dep_date),
                "Departure_Time": dep_time,
                "Departure_Place": dep_place,
                "Arrival_Date": pd.to_datetime(arr_date),
                "Arrival_Time": arr_time,
                "Arrival_Place": arr_place,
                "Mode_of_Travel": mode,
                "Purpose": purpose
            }
            # Add, Sort, Update
            st.session_state['raw_diary_df'] = pd.concat([st.session_state['raw_diary_df'], pd.DataFrame([new_row])], ignore_index=True)
            st.session_state['raw_diary_df'] = sort_diary(st.session_state['raw_diary_df'])
            st.success("Journey Added & Sorted!")
            st.rerun()

# --- TAB 2: ADD STAY ---
with tab_stay:
    st.caption("Use this to record a night halt or stay at a hotel.")
    with st.form("add_stay_form", clear_on_submit=True):
        s1, s2, s3 = st.columns(3)
        stay_place = s1.text_input("Place of Stay (e.g. Hotel X)")
        stay_date_in = s2.date_input("Check-in / Start Date")
        stay_time_in = s3.time_input("Check-in Time", value=time(20, 0)) # Default 8 PM
        
        s4, s5, s6 = st.columns(3)
        stay_remark = s4.text_input("Remark", value="Night Halt")
        stay_date_out = s5.date_input("Check-out / End Date")
        stay_time_out = s6.time_input("Check-out Time", value=time(8, 0)) # Default 8 AM

        if st.form_submit_button("Add Stay Record"):
            new_row = {
                "Departure_Date": pd.to_datetime(stay_date_in),
                "Departure_Time": stay_time_in,
                "Departure_Place": stay_place,
                "Arrival_Date": pd.to_datetime(stay_date_out),
                "Arrival_Time": stay_time_out,
                "Arrival_Place": stay_place, # Stay is same place
                "Mode_of_Travel": "None",
                "Purpose": stay_remark
            }
            st.session_state['raw_diary_df'] = pd.concat([st.session_state['raw_diary_df'], pd.DataFrame([new_row])], ignore_index=True)
            st.session_state['raw_diary_df'] = sort_diary(st.session_state['raw_diary_df'])
            st.success("Stay Added & Sorted!")
            st.rerun()

st.markdown("---")

# ==========================================
# SECTION: VIEW & EDIT TABLE
# ==========================================
st.info("👇 **Review Your Schedule** (Rows are automatically sorted by Date/Time)")

edited_diary = st.data_editor(
    st.session_state['raw_diary_df'],
    num_rows="dynamic",
    use_container_width=True,
    key="diary_editor",
    column_config={
        "Departure_Date": st.column_config.DateColumn("Dep Date", format="DD-MM-YYYY"),
        "Departure_Time": st.column_config.TimeColumn("Dep Time", format="HH:mm"),
        "Departure_Place": st.column_config.TextColumn("Dep Place"),
        
        "Arrival_Date": st.column_config.DateColumn("Arr Date", format="DD-MM-YYYY"),
        "Arrival_Time": st.column_config.TimeColumn("Arr Time", format="HH:mm"),
        "Arrival_Place": st.column_config.TextColumn("Arr Place"),
        
        "Mode_of_Travel": st.column_config.SelectboxColumn(
            "Mode", 
            options=["Bus", "Rail", "Auto Rickshaw", "Taxi", "Govt Vehicle", "Private Car", "Air", "None"],
            required=True
        ),
        "Purpose": st.column_config.TextColumn("Purpose")
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
        st.switch_page("pages/4_🧮_TA_DA_Calc.py")
