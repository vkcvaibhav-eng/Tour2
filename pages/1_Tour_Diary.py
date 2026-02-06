import streamlit as st
import pandas as pd
import utils
import os
import json
from datetime import datetime

st.set_page_config(layout="wide", page_title="Step 1: Tour Diary")
st.title("🗓️ Step 1: Tour Diary")

# Validation
if not st.session_state.get('gemini_api_key'):
    st.error("⚠️ Please go to 'Home' and enter your Gemini API Key first.")
    st.stop()

# --- HELPER: CONVERT STRINGS TO OBJECTS ---
def cleanup_data_types(df):
    """
    Converts text dates/times to actual Python Date/Time objects
    so Streamlit's data_editor doesn't crash.
    """
    # 1. Convert Dates (Assumes AI outputs DD-MM-YYYY or YYYY-MM-DD)
    date_cols = ["Departure_Date", "Arrival_Date"]
    for col in date_cols:
        if col in df.columns:
            # errors='coerce' turns bad data into NaT (empty) instead of crashing
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce').dt.date

    # 2. Convert Times (Assumes HH:MM)
    time_cols = ["Departure_Time", "Arrival_Time"]
    for col in time_cols:
        if col in df.columns:
            # We use a custom lambda to handle time parsing safely
            def parse_time(t):
                if pd.isna(t) or str(t).strip() == "": return None
                try:
                    # Try 24hr format first
                    return datetime.strptime(str(t).strip(), "%H:%M").time()
                except:
                    return None # Return empty if format is weird
            
            df[col] = df[col].apply(parse_time)
            
    return df

# --- PART A: UPLOAD ---
st.subheader("1. Upload Tour Diary")
st.info("Upload your scanned Tour Diary (PDF or Image).")

uploaded_diary = st.file_uploader("Select File", type=['pdf', 'jpg', 'jpeg', 'png'])

# Temp storage for extraction
TEMP_DIR = "temp_processing"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

if uploaded_diary:
    # Save file locally for the AI to read
    file_path = os.path.join(TEMP_DIR, uploaded_diary.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_diary.getbuffer())
    
    if st.button("🚀 Extract Data from Diary"):
        with st.spinner("AI is reading the tour diary..."):
            try:
                # Specific Prompt for Diary
                prompt = """
                Extract the tour diary details into a JSON structure under the key "tour_diary".
                Fields required: "Departure_Date" (DD-MM-YYYY), "Departure_Time" (HH:MM 24hr), "Departure_Place", 
                "Arrival_Date" (DD-MM-YYYY), "Arrival_Time" (HH:MM 24hr), "Arrival_Place", 
                "Mode_of_Travel" (e.g., Bus, Rail, Auto, Private Vehicle), "Purpose".
                ENSURE TIMES ARE STRICTLY HH:MM (24 hour format).
                Return ONLY valid JSON.
                """
                
                # Call Utility
                response_text = utils.call_gemini_extraction(
                    st.session_state['gemini_api_key'],
                    [file_path],
                    prompt
                )
                
                # Parse JSON
                data = utils.clean_and_parse_json(response_text)
                
                # Normalize into DataFrame
                if "tour_diary" in data:
                    df = pd.DataFrame(data["tour_diary"])
                else:
                    df = pd.DataFrame(data)
                
                # --- FIX: CLEAN TYPES BEFORE SAVING ---
                df = cleanup_data_types(df)
                
                # Save to session
                st.session_state['raw_diary_df'] = df
                st.session_state['diary_uploaded'] = True
                st.success("Extraction Complete!")
                st.rerun() # Refresh to show the editor
                
            except Exception as e:
                st.error(f"Error during extraction: {str(e)}")

# --- PART B: EDIT ---
if st.session_state.get('diary_uploaded') and 'raw_diary_df' in st.session_state:
    st.divider()
    st.subheader("2. Review & Edit")
    
    # Ensure types are correct even if reloading from session
    df_to_edit = st.session_state['raw_diary_df']
    
    # Try/Except block for the editor specifically
    try:
        edited_df = st.data_editor(
            df_to_edit,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Departure_Date": st.column_config.DateColumn("Dep Date", format="DD-MM-YYYY"),
                "Departure_Time": st.column_config.TimeColumn("Dep Time", format="HH:mm"),
                "Departure_Place": st.column_config.TextColumn("From"),
                "Arrival_Date": st.column_config.DateColumn("Arr Date", format="DD-MM-YYYY"),
                "Arrival_Time": st.column_config.TimeColumn("Arr Time", format="HH:mm"),
                "Arrival_Place": st.column_config.TextColumn("To"),
                "Mode_of_Travel": st.column_config.SelectboxColumn(
                    "Mode", 
                    options=["Bus", "Rail", "Private Vehicle", "Government Vehicle", "Auto", "Taxi"]
                ),
                "Purpose": st.column_config.TextColumn("Purpose"),
            }
        )
        
        # Save Final State
        st.session_state['final_tour_diary'] = edited_df
        
        st.markdown("---")
        st.success("✅ Data saved. Proceed to 'Step 2: TA Calculation' in the sidebar.")
        
    except Exception as e:
        st.error(f"Data Type Error: {e}")
        st.warning("Trying to reset data types... Please click 'Extract' again if this persists.")
