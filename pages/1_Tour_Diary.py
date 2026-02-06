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
            # Handle both string and datetime objects safely
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce').dt.date

    # 2. Convert Times
    time_cols = ["Departure_Time", "Arrival_Time"]
    for col in time_cols:
        if col in df.columns:
            def parse_time(t):
                if pd.isna(t) or t == "": return None
                if isinstance(t, time): return t # Already a time object
                try:
                    # Clean string and try convert
                    t_str = str(t).strip()
                    if len(t_str) > 5: t_str = t_str[:5] # Handle HH:MM:SS
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

# Temp storage
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
                "Mode_of_Travel", "Purpose", "KM", "Ticket_Price".
                ENSURE TIMES ARE HH:MM (24hr).
                """
                response_text = utils.call_gemini_extraction(
                    st.session_state['gemini_api_key'], [file_path], prompt
                )
                
                # Parse & Clean
                data = utils.clean_and_parse_json(response_text)
                if "tour_diary" in data:
                    df = pd.DataFrame(data["tour_diary"])
                else:
                    df = pd.DataFrame(data)
                
                # Ensure Columns Exist
                req_cols = ["Departure_Place", "Departure_Date", "Departure_Time", 
                           "Arrival_Place", "Arrival_Date", "Arrival_Time", 
                           "Mode_of_Travel", "Purpose"]
                for c in req_cols:
                    if c not in df.columns: df[c] = None

                # Clean Types & Sort
                df = cleanup_data_types(df)
                df = sort_diary(df)
                
                st.session_state['raw_diary_df'] = df
                st.session_state['diary_uploaded'] = True
                st.success("Extraction Complete!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error during extraction: {str(e)}")

# --- PART B: MANUAL ADD & EDIT ---
if st.session_state.get('diary_uploaded') or 'raw_diary_df' in st.session_state:
    
    # Initialize if empty
    if 'raw_diary_df' not in st.session_state:
        st.session_state['raw_diary_df'] = pd.DataFrame(columns=[
            "Departure_Place", "Departure_Date", "Departure_Time", 
            "Arrival_Place", "Arrival_Date", "Arrival_Time", 
            "Mode_of_Travel", "Purpose"
        ])

    st.divider()
    
    # === MANUAL ENTRY TABS ===
    st.markdown("### ➕ Add Details Manually")
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
            c7, c8 = st.columns([1.5, 2])
            with c7:
                base_mode = st.selectbox("7. Mode", ["Bus", "Rail", "Private Vehicle", "University Vehicle", "Auto Rickshaw", "Flight", "Taxi"])
                final_mode = base_mode
                if base_mode == "University Vehicle":
                    veh_no = st.text_input("Vehicle Number (e.g. GJ-XX-1234)")
                    if veh_no: final_mode = f"University Vehicle ({veh_no})"

            purpose = c8.text_input("8. Purpose", value="Official Work")

            if st.form_submit_button("Add Journey"):
                new_row = {
                    "Departure_Place": dep_place, "Departure_Date": dep_date, "Departure_Time": dep_time,
                    "Arrival_Place": arr_place, "Arrival_Date": arr_date, "Arrival_Time": arr_time,
                    "Mode_of_Travel": final_mode, "Purpose": purpose
                }
                st.session_state['raw_diary_df'] = pd.concat([st.session_state['raw_diary_df'], pd.DataFrame([new_row])], ignore_index=True)
                st.session_state['raw_diary_df'] = cleanup_data_types(st.session_state['raw_diary_df']) # Ensure types match
                st.session_state['raw_diary_df'] = sort_diary(st.session_state['raw_diary_df'])
                st.rerun()

    # --- TAB 2: ADD STAY ---
    with tab_stay:
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
                    "Departure_Place": stay_place, "Departure_Date": stay_date_in, "Departure_Time": stay_time_in,
                    "Arrival_Place": stay_place, "Arrival_Date": stay_date_out, "Arrival_Time": stay_time_out,
                    "Mode_of_Travel": "None", "Purpose": stay_remark
                }
                st.session_state['raw_diary_df'] = pd.concat([st.session_state['raw_diary_df'], pd.DataFrame([new_row])], ignore_index=True)
                st.session_state['raw_diary_df'] = cleanup_data_types(st.session_state['raw_diary_df'])
                st.session_state['raw_diary_df'] = sort_diary(st.session_state['raw_diary_df'])
                st.rerun()

    # === REVIEW & EDIT ===
    st.subheader("2. Review & Edit")
    
    # Reorder Columns for Display (Place -> Date -> Time)
    display_order = [
        "Departure_Place", "Departure_Date", "Departure_Time", 
        "Arrival_Place", "Arrival_Date", "Arrival_Time", 
        "Mode_of_Travel", "Purpose"
    ]
    
    # Ensure all cols exist
    df_to_edit = st.session_state['raw_diary_df']
    for c in display_order: 
        if c not in df_to_edit.columns: df_to_edit[c] = None
    
    edited_df = st.data_editor(
        df_to_edit[display_order],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Departure_Place": st.column_config.TextColumn("1. From Place"),
            "Departure_Date": st.column_config.DateColumn("2. Dep Date", format="DD-MM-YYYY"),
            "Departure_Time": st.column_config.TimeColumn("3. Dep Time", format="HH:mm"),
            
            "Arrival_Place": st.column_config.TextColumn("4. To Place"),
            "Arrival_Date": st.column_config.DateColumn("5. Arr Date", format="DD-MM-YYYY"),
            "Arrival_Time": st.column_config.TimeColumn("6. Arr Time", format="HH:mm"),
            
            "Mode_of_Travel": st.column_config.TextColumn(
                "7. Mode", 
                help="Type details like: 'University Vehicle (GJ-21-1234)' or 'Private Car'"
            ),
            "Purpose": st.column_config.TextColumn("8. Purpose"),
        }
    )
    
    st.session_state['final_tour_diary'] = edited_df
    
    st.markdown("---")
    if st.button("✅ Confirm & Go to Calc"):
        st.session_state['final_tour_diary'] = edited_df
        # Make sure your next page is named EXACTLY like this:
        st.switch_page("pages/2_TA_Calculation.py")

