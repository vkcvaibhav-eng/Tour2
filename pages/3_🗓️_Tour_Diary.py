import streamlit as st
import pandas as pd
import json

st.set_page_config(layout="wide")
st.title("🗓️ Edit Tour Diary (Schedule)")

if 'extracted_data' not in st.session_state:
    st.warning("No data found. Please go to 'Upload & Extract' first.")
    st.stop()

# --- 1. Load Raw Data from AI ---
if 'raw_diary_df' not in st.session_state:
    # Parse the AI response from Page 2
    raw_response = st.session_state['extracted_data']
    try:
        # Basic JSON cleaning
        if "```json" in raw_response:
            clean_json = raw_response.split("```json")[1].split("```")[0]
            data = json.loads(clean_json)
        elif "```" in raw_response:
            clean_json = raw_response.split("```")[1].split("```")[0]
            data = json.loads(clean_json)
        else:
            data = json.loads(raw_response)
    except:
        st.error("Could not parse AI data. Please re-extract.")
        st.stop()

    # Extract just the tour diary part
    diary_data = data.get("tour_diary", [])
    
    # Define the exact columns you want for the Excel-like format
    cols = [
        "Departure_Place", "Departure_Date", "Departure_Time",
        "Arrival_Place", "Arrival_Date", "Arrival_Time",
        "Mode_of_Travel"
    ]
    
    # Create DataFrame
    st.session_state['raw_diary_df'] = pd.DataFrame(diary_data, columns=cols)

# --- 2. The Editable Table ---
st.info("Step 1: Verify your journey details below. Add missing rows or fix times here.")

# Data Editor allows adding/deleting rows (num_rows="dynamic")
edited_diary = st.data_editor(
    st.session_state['raw_diary_df'],
    num_rows="dynamic",
    use_container_width=True,
    key="diary_editor",
    column_config={
        "Departure_Time": st.column_config.TimeColumn(format="HH:mm"),
        "Arrival_Time": st.column_config.TimeColumn(format="HH:mm"),
        "Departure_Date": st.column_config.DateColumn(format="DD-MM-YYYY"),
        "Arrival_Date": st.column_config.DateColumn(format="DD-MM-YYYY"),
    }
)

st.markdown("---")

# --- 3. Save & Proceed ---
col1, col2 = st.columns([3, 1])
with col1:
    st.caption("Once this table is correct, click 'Confirm' to proceed to Money Calculation.")
with col2:
    if st.button("✅ Confirm Tour Diary"):
        # Save the polished data to a specific session variable
        st.session_state['final_tour_diary'] = edited_diary
        st.success("Tour Diary Saved! Please go to **Page 4: TA & DA Calculation**.")
