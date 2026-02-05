import streamlit as st
import pandas as pd
import json

st.set_page_config(layout="wide")
st.title("📝 Review & Calculate")

if 'extracted_data' not in st.session_state:
    st.warning("No data found. Please go to 'Upload & Extract' first.")
    st.stop()

# --- parsing logic ---
raw_response = st.session_state['extracted_data']
try:
    # Clean the markdown JSON if present
    if "```json" in raw_response:
        clean_json = raw_response.split("```json")[1].split("```")[0]
        data = json.loads(clean_json)
    elif "```" in raw_response:
        clean_json = raw_response.split("```")[1].split("```")[0]
        data = json.loads(clean_json)
    else:
        data = json.loads(raw_response)
except:
    st.error("Error parsing AI response. Showing raw text instead.")
    st.text(raw_response)
    st.stop()

# --- TABS FOR SEPARATE TASKS ---
tab1, tab2, tab3 = st.tabs(["1️⃣ Tour Diary (Exact)", "2️⃣ TA Calculation", "3️⃣ DA Calculation"])

# === TAB 1: TOUR DIARY (Strict Extraction) ===
with tab1:
    st.header("Tour Diary (Arrival & Dispatch)")
    st.caption("This data is extracted strictly from your uploaded Tour Diary PDF columns.")
    
    # Defined columns as per NAU Tour Diary
    diary_cols = [
        "Dispatch_Station", "Dispatch_Date", "Dispatch_Hour",
        "Arrival_Station", "Arrival_Date", "Arrival_Hour",
        "Mode_of_Travel", "Distance_km", "Purpose"
    ]
    
    # Initialize session state for this table
    if 'diary_df' not in st.session_state:
        st.session_state['diary_df'] = pd.DataFrame(data.get('tour_diary', []), columns=diary_cols)
    
    # Editable Table
    st.session_state['diary_df'] = st.data_editor(
        st.session_state['diary_df'], 
        num_rows="dynamic", 
        use_container_width=True,
        key="editor_diary"
    )

# === TAB 2: TA CALCULATION (Tickets) ===
with tab2:
    st.header("TA Calculation (Travel Allowance)")
    st.caption("Enter Ticket Numbers and Fare Amounts here.")
    
    ta_cols = ["Mode", "From_Station", "To_Station", "Ticket_No", "Fare_Amount", "Remark"]
    
    if 'ta_df' not in st.session_state:
        st.session_state['ta_df'] = pd.DataFrame(data.get('ta_data', []), columns=ta_cols)
        
    st.session_state['ta_df'] = st.data_editor(
        st.session_state['ta_df'], 
        num_rows="dynamic", 
        use_container_width=True,
        key="editor_ta"
    )
    
    # Quick Sum
    total_ta = pd.to_numeric(st.session_state['ta_df']['Fare_Amount'], errors='coerce').sum()
    st.success(f"Total TA Claim: ₹ {total_ta}")

# === TAB 3: DA CALCULATION (Daily Allowance) ===
with tab3:
    st.header("DA Calculation (Daily Allowance)")
    st.caption("Calculate Days * Rate.")
    
    da_cols = ["Date", "Stay_Location", "Pay_Level", "DA_Rate", "Days_Claimed", "Total_DA"]
    
    if 'da_df' not in st.session_state:
        # Generate rows based on dates if empty, or use AI extracted
        st.session_state['da_df'] = pd.DataFrame(data.get('da_data', []), columns=da_cols)
        
    st.session_state['da_df'] = st.data_editor(
        st.session_state['da_df'], 
        num_rows="dynamic", 
        use_container_width=True,
        key="editor_da"
    )
    
    # Quick Sum
    total_da = pd.to_numeric(st.session_state['da_df']['Total_DA'], errors='coerce').sum()
    st.success(f"Total DA Claim: ₹ {total_da}")

st.markdown("---")
if st.button("💾 Confirm All & Ready for Export"):
    st.session_state['final_diary'] = st.session_state['diary_df']
    st.session_state['final_ta'] = st.session_state['ta_df']
    st.session_state['final_da'] = st.session_state['da_df']
    st.success("All data confirmed! Go to the 'Export' page to download.")
