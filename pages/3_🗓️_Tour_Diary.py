import streamlit as st
import pandas as pd
import json

st.set_page_config(layout="wide")
st.title("📝 Review & Calculate")

if 'extracted_data' not in st.session_state:
    st.warning("No data found. Please go to 'Upload & Extract' first.")
    st.stop()

# --- Parsing Logic ---
raw_response = st.session_state['extracted_data']

# Try to parse JSON from AI response
try:
    if "```json" in raw_response:
        clean_json = raw_response.split("```json")[1].split("```")[0]
        data = json.loads(clean_json)
    elif "```" in raw_response:
        clean_json = raw_response.split("```")[1].split("```")[0]
        data = json.loads(clean_json)
    else:
        data = json.loads(raw_response)
except:
    st.error("Error parsing AI response. Showing raw text.")
    st.text(raw_response)
    st.stop()

# Show User Context (Extracted from Salary Slip)
user_details = data.get("user_details", {})
if user_details:
    st.info(f"👤 **Identified User:** {user_details.get('name')} | **Level:** {user_details.get('pay_level')} | **Rule Used:** {user_details.get('rule_used')}")

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["1️⃣ Tour Diary", "2️⃣ TA Calculation", "3️⃣ DA Calculation (Smart)"])

# === TAB 1: DIARY ===
with tab1:
    st.header("Tour Diary")
    diary_cols = ["Dispatch_Station", "Dispatch_Date", "Dispatch_Hour", "Arrival_Station", "Arrival_Date", "Arrival_Hour", "Mode_of_Travel", "Purpose"]
    
    if 'diary_df' not in st.session_state:
        st.session_state['diary_df'] = pd.DataFrame(data.get('tour_diary', []), columns=diary_cols)
    
    st.session_state['diary_df'] = st.data_editor(st.session_state['diary_df'], num_rows="dynamic", use_container_width=True, key="diary")

# === TAB 2: TA (TICKETS) ===
with tab2:
    st.header("TA Calculation")
    ta_cols = ["Mode", "Ticket_No", "Fare_Amount", "Remark"]
    
    if 'ta_df' not in st.session_state:
        st.session_state['ta_df'] = pd.DataFrame(data.get('ta_data', []), columns=ta_cols)
        
    st.session_state['ta_df'] = st.data_editor(st.session_state['ta_df'], num_rows="dynamic", use_container_width=True, key="ta")

# === TAB 3: DA (DURATION BASED) ===
with tab3:
    st.header("DA Calculation")
    st.caption("AI calculated duration based on Pay Level & Statutes.")
    
    # Columns matching the "Smart" extraction
    da_cols = ["Date", "Start_Time", "End_Time", "Duration_Hours", "Rate_Applied", "DA_Amount"]
    
    if 'da_df' not in st.session_state:
        st.session_state['da_df'] = pd.DataFrame(data.get('da_calculation', []), columns=da_cols)
        
    st.session_state['da_df'] = st.data_editor(st.session_state['da_df'], num_rows="dynamic", use_container_width=True, key="da")
    
    # Total
    total_da = pd.to_numeric(st.session_state['da_df']['DA_Amount'], errors='coerce').sum()
    st.success(f"💰 Total DA Calculated: ₹ {total_da}")

st.markdown("---")
if st.button("💾 Confirm All & Ready for Export"):
    st.session_state['final_diary'] = st.session_state['diary_df']
    st.session_state['final_ta'] = st.session_state['ta_df']
    st.session_state['final_da'] = st.session_state['da_df']
    st.success("Data ready! Go to 'Export' page.")
