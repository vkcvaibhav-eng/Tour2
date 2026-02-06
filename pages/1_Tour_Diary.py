import streamlit as st
import pandas as pd
import utils
import os
import json
from datetime import datetime, time

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
        if "(" in mode_str: return mode_str # Keep existing number
        return "University Vehicle"
    return mode_str.title()

def sort_diary(df):
    """Sorts the diary chronologically by Departure Date and Time."""
    try:
        # Create temp column for sorting
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
    """Converts mixed text/objects to actual Python Date/Time objects."""
    # 1. Convert Dates
    date_cols = ["Departure_Date", "Arrival_Date"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce').dt.date

    # 2. Convert Times
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
            
    # 3. Clean Modes
    if "Mode_of_Travel" in df.columns:
        df["Mode_of_Travel"] = df["Mode_of_Travel"].apply(clean_mode_name)
        
    return df

# --- PART A: UPLOAD ---
st.subheader("1. Upload Tour Diary")
st.info("Upload your scanned Tour Diary (PDF or Image).")

uploaded_diary = st.file_uploader("Select File", type=['pdf', 'jpg', 'jpeg', 'png'])

TEMP_DIR = "temp_processing"
if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)

if uploaded_diary:
    file_path = os.path.join(TEMP_DIR, uploaded_diary.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_diary.getbuffer())

    if st.button("🚀 Extract Data from Diary"):
        with st.spinner("AI is reading the tour diary..."):
            try:
                # Included KM in extraction prompt
                prompt = """
                Extract the tour diary details into JSON key "tour_diary". 
                Fields: "Departure_Date", "Departure_Time", "Departure_Place", 
                "Arrival_Date", "Arrival_Time", "Arrival_Place", 
                "Mode_of_Travel", "KM", "Purpose". 
                ENSURE TIMES ARE HH:MM (24hr).
                """
                response_text = utils.call_gemini_extraction(
                    st.session_state['gemini_api_key'], 
                    [file_path], 
                    prompt
                )
                
                data = utils.clean_and_parse_json(response_text)
                if "tour_diary" in data:
                    df = pd.DataFrame(data["tour_diary"])
                    df = cleanup_data_types(df)
                    df = sort_diary(df)
                    st.session_state['raw_diary_df'] = df
                    st.success("✅ Extraction Complete!")
            except Exception as e:
                st.error(f"Error during extraction: {e}")

# --- PART B: EDIT ---
if 'raw_diary_df' in st.session_state:
    st.subheader("2. Review & Edit extracted Diary")
    
    # Updated display sequence: KM is column 11, Purpose is column 18
    display_order = [
        "Departure_Place", "Departure_Date", "Departure_Time",
        "Arrival_Place", "Arrival_Date", "Arrival_Time",
        "Mode_of_Travel", "KM", "Purpose"
    ]
    
    df_to_edit = st.session_state['raw_diary_df']
    for c in display_order: 
        if c not in df_to_edit.columns: 
            df_to_edit[c] = None
    
    # Data editor configuration with custom column numbering
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

    if st.button("💾 Save & Continue"):
        st.session_state['tour_diary_df'] = edited_df
        st.success("Tour diary data saved! You can now proceed to the next step.")
