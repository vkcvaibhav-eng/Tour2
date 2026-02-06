import streamlit as st
import pandas as pd
import utils
import os
import json

st.set_page_config(layout="wide", page_title="Tour Diary")
st.title("🗓️ Step 1: Tour Diary")

if 'gemini_api_key' not in st.session_state or not st.session_state['gemini_api_key']:
    st.error("Please set your Gemini API Key on the Home page first.")
    st.stop()

# --- SECTION 1: UPLOAD & EXTRACT ---
st.subheader("1. Upload Tour Diary")
uploaded_diary = st.file_uploader("Upload Scanned Tour Diary (PDF/Image)", type=['pdf', 'jpg', 'png'])

if uploaded_diary:
    if st.button("🚀 Extract Diary Data"):
        with st.spinner("AI is reading your diary..."):
            # Save file temporarily for processing
            temp_path = f"temp_diary_{uploaded_diary.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_diary.getbuffer())
            
            # Call Extraction (using your utils function)
            # We specifically ask for Tour Diary fields
            prompt = """
            Extract the tour diary details into a JSON format with these exact keys:
            "Departure_Date", "Departure_Time", "Departure_Place", 
            "Arrival_Date", "Arrival_Time", "Arrival_Place", 
            "Mode_of_Travel", "Purpose".
            Format dates as DD-MM-YYYY and times as HH:MM.
            """
            
            raw_response = utils.call_gemini_extraction(
                st.session_state['gemini_api_key'], 
                [temp_path],
                prompt
            )
            
            # Clean up temp file
            os.remove(temp_path)
            
            # Save Raw Response
            st.session_state['extracted_diary_json'] = raw_response
            
            # Attempt to Parse JSON to DataFrame
            try:
                # Basic parsing logic (assuming response is JSON string)
                json_str = raw_response
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0]
                
                data = json.loads(json_str)
                # Handle if it returns a dict with a key like 'tour_diary' or a list directly
                if isinstance(data, dict) and 'tour_diary' in data:
                    df = pd.DataFrame(data['tour_diary'])
                else:
                    df = pd.DataFrame(data)
                
                st.session_state['raw_diary_df'] = df
                st.session_state['diary_ready'] = True
                
            except Exception as e:
                st.error(f"Error parsing AI response: {e}")
                st.text(raw_response) # Debug view

# --- SECTION 2: EDIT ---
if st.session_state.get('diary_ready'):
    st.divider()
    st.subheader("2. Edit & Verify Entries")
    
    edited_diary = st.data_editor(
        st.session_state['raw_diary_df'],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Departure_Date": st.column_config.DateColumn("Dep Date", format="DD-MM-YYYY"),
            "Departure_Time": st.column_config.TimeColumn("Dep Time", format="HH:mm"),
            "Departure_Place": st.column_config.TextColumn("From"),
            "Arrival_Date": st.column_config.DateColumn("Arr Date", format="DD-MM-YYYY"),
            "Arrival_Time": st.column_config.TimeColumn("Arr Time", format="HH:mm"),
            "Arrival_Place": st.column_config.TextColumn("To"),
            "Mode_of_Travel": st.column_config.TextColumn("Mode"),
            "Purpose": st.column_config.TextColumn("Purpose"),
        }
    )
    
    st.session_state['final_tour_diary'] = edited_diary
    
    st.success("✅ Diary Data Ready for TA Calculation.")
