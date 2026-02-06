import streamlit as st
import pandas as pd
import utils
import os
import json
from datetime import datetime, time, date

st.set_page_config(layout="wide", page_title="Step 1: Tour Diary")
st.title("🗓️ Step 1: Tour Diary")

# Validation
if not st.session_state.get('gemini_api_key'):
    st.error("⚠️ Please go to 'Home' and enter your Gemini API Key first.")
    st.stop()

# --- HELPER FUNCTIONS ---

def clean_mode_name(mode_str):
    """Standardizes mode names (Car -> Private Vehicle, etc.)"""
    if not isinstance(mode_str, str): return mode_str
    m = mode_str.lower().strip()
    if m in ["car", "personal car", "own car", "jeep", "cab"]: return "Private Vehicle"
    if "auto" in m or "rickshaw" in m: return "Auto Rickshaw"
    if "flight" in m or "air" in m: return "Flight"
    if "rail" in m or "train" in m: return "Rail"
    if "uni" in m or "govt" in m:
        if "(" in mode_str: return mode_str 
        return "University Vehicle"
    return mode_str.title()

def sort_diary(df):
    """Sorts the diary chronologically."""
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

def cleanup_data_types(df):
    """Converts text/objects to actual Python Date/Time objects."""
    date_cols = ["Departure_Date", "Arrival_Date"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce').dt.date

    time_cols = ["Departure_Time", "Arrival_Time"]
    for col in time_cols:
        if col in df.columns:
            def parse_time(t):
                if pd.isna(t) or t == "": return None
                if isinstance(t, time): return t
                try:
                    t_str = str(t).strip()
                    if len(t_str) > 5: t_str = t_str[:5]
                    return datetime.strptime(t_str, "%H:%M").time()
                except:
                    return None
            df[col] = df[col].apply(parse_time)
            
    if "Mode_of_Travel" in df.columns:
        df["Mode_of_Travel"] = df["Mode_of_Travel"].apply(clean_mode_name)
    return df

# --- INITIALIZE STATE ---
if 'raw_diary_df' not in st.session_state:
    # Create empty dataframe with correct columns if nothing is uploaded yet
    st.session_state['raw_diary_df'] = pd.DataFrame(columns=[
        "Departure_Place", "Departure_Date", "Departure_Time",
        "Arrival_Place", "Arrival_Date", "Arrival_Time",
        "Mode_of_Travel", "KM", "Purpose"
    ])

# --- PART A: UPLOAD ---
st.subheader("1. Upload Tour Diary")
uploaded_diary = st.file_uploader("Upload scanned Tour Diary (PDF/Image)", type=['pdf', 'jpg', 'jpeg', 'png'])

TEMP_DIR = "temp_processing"
if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)

if uploaded_diary:
    file_path = os.path.join(TEMP_DIR, uploaded_diary.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_diary.getbuffer())

    if st.button("🚀 Extract Data from Diary"):
        with st.spinner("AI is reading the tour diary..."):
            try:
                prompt = """
                Extract the tour diary details into JSON key "tour_diary". 
                Fields: "Departure_Date", "Departure_Time", "Departure_Place", 
                "Arrival_Date", "Arrival_Time", "Arrival_Place", 
                "Mode_of_Travel", "KM", "Purpose". 
                ENSURE TIMES ARE HH:MM (24hr).
                """
                response_text = utils.call_gemini_extraction(
                    st.session_state['gemini_api_key'], [file_path], prompt
                )
                data = utils.clean_and_parse_json(response_text)
                if "tour_diary" in data:
                    df = pd.DataFrame(data["tour_diary"])
                    df = cleanup_data_types(df)
                    st.session_state['raw_diary_df'] = sort_diary(df)
                    st.success("✅ Extraction Complete!")
            except Exception as e:
                st.error(f"Error: {e}")

# --- NEW FEATURE: MANUAL ADD BUTTONS ---
st.markdown("---")
st.subheader("➕ Manual Entry Options")
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

with col_btn1:
    if st.button("➕ Add Blank Journey"):
        new_row = pd.DataFrame([{
            "Departure_Date": date.today(), "Departure_Time": time(9, 0),
            "Arrival_Date": date.today(), "Arrival_Time": time(10, 0),
            "KM": 0.0, "Mode_of_Travel": "Bus"
        }])
        st.session_state['raw_diary_df'] = pd.concat([st.session_state['raw_diary_df'], new_row], ignore_index=True)
        st.rerun()

with col_btn2:
    if st.button("🏨 Add Stay / Halt"):
        new_row = pd.DataFrame([{
            "Departure_Place": "STAY / HALT",
            "Departure_Date": date.today(), "Departure_Time": time(0, 0),
            "Arrival_Place": "STAY / HALT",
            "Arrival_Date": date.today(), "Arrival_Time": time(23, 59),
            "Mode_of_Travel": "STAY", "KM": 0.0, "Purpose": "Night Halt"
        }])
        st.session_state['raw_diary_df'] = pd.concat([st.session_state['raw_diary_df'], new_row], ignore_index=True)
        st.rerun()

with col_btn3:
    if st.button("🧹 Clear All Rows"):
        st.session_state['raw_diary_df'] = st.session_state['raw_diary_df'].iloc[0:0]
        st.rerun()

# --- PART B: EDIT ---
if not st.session_state['raw_diary_df'].empty:
    st.subheader("2. Review & Edit extracted Diary")
    
    display_order = [
        "Departure_Place", "Departure_Date", "Departure_Time",
        "Arrival_Place", "Arrival_Date", "Arrival_Time",
        "Mode_of_Travel", "KM", "Purpose"
    ]
    
    df_to_edit = st.session_state['raw_diary_df']
    # Ensure all columns exist
    for c in display_order: 
        if c not in df_to_edit.columns: df_to_edit[c] = None
    
    edited_df = st.data_editor(
        df_to_edit[display_order],
        num_rows="dynamic",
        key="diary_editor",
        use_container_width=True,
        column_config={
            "Departure_Place": st.column_config.TextColumn("1. Departure place"),
            "Departure_Date": st.column_config.DateColumn("2. Departure Date", format="DD-MM-YYYY"),
            "Departure_Time": st.column_config.TimeColumn("3. Departure time", format="HH:mm"),
            "Arrival_Place": st.column_config.TextColumn("4. Arrival place"),
            "Arrival_Date": st.column_config.DateColumn("5. Arrival Date", format="DD-MM-YYYY"),
            "Arrival_Time": st.column_config.TimeColumn("6. Arrival Time", format="HH:mm"),
            "Mode_of_Travel": st.column_config.TextColumn("7. Mode"),
            "KM": st.column_config.NumberColumn("11. KM", format="%.1f"),
            "Purpose": st.column_config.TextColumn("18. Purpose of Journey"),
        }
     )
    
    # Sync edited data back to session state
    st.session_state['raw_diary_df'] = edited_df
    
    st.markdown("---")
    if st.button("✅ Confirm & Go to Calculation"):
        st.session_state['final_tour_diary'] = edited_df
        st.switch_page("pages/2_TA_Calculation.py")
