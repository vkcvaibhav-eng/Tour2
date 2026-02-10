import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import io
import numpy as np # Added for safer conditional calculations
from PIL import Image
from datetime import datetime

# ==========================================
# ⚙️ CONFIGURATION & SETUP
# ==========================================
st.set_page_config(layout="wide", page_title="Step 2: TA Calculation & AI Validation")

api_key = st.session_state.get('gemini_api_key')
if not api_key:
    st.error("⚠️ Gemini API Key not found. Please set it in the Home page.")
    st.stop()

genai.configure(api_key=api_key)

# --- EXACT COLUMN NAME DEFINITIONS ---
COL1 = "1. Departure Place"
COL2 = "2. Departure Date"
COL3 = "3. Departure Time"
COL4 = "4. Arrival Place"
COL5 = "5. Arrival Date"
COL6 = "6. Arrival Time"
COL7 = "7. Mode"
COL8 = "8. Class"
COL9 = "9. Ticket Price/Rate (Rs.)"
COL10 = "10. Actual Total Amount of Ticket (Rs.)"
COL11 = "11. KM"
COL12 = "12. Rate (Rs.) (Auto/Taxi/Pvt)"
COL13 = "13. Total (Rs.)"
COL18 = "18. Purpose of Journey"

ALL_COLS = [COL1, COL2, COL3, COL4, COL5, COL6, COL7, COL8, COL9, COL10, COL11, COL12, COL13, COL18]

# ==========================================
# 🧠 HELPERS
# ==========================================
def try_get_km_from_raw(dep_date, dep_place):
    raw_data = st.session_state.get('extracted_data', {})
    if isinstance(raw_data, str):
        try:
            if "```json" in raw_data:
                raw_data = json.loads(raw_data.split("```json")[1].split("```")[0])
            elif "```" in raw_data:
                raw_data = json.loads(raw_data.split("```")[1].split("```")[0])
        except: return 0.0
    if isinstance(raw_data, list):
        for entry in raw_data:
            if str(entry.get('Departure Date')) == str(dep_date) and entry.get('Departure Place') == dep_place:
                return float(entry.get('KM', 0))
    return 0.0

def extract_data_from_documents(uploaded_files):
    if not uploaded_files: return []
    results = []
    progress_bar = st.progress(0)
    for i, file in enumerate(uploaded_files):
        try:
            image_data = file.getvalue()
            image_parts = [{"mime_type": file.type, "data": image_data}]
            
            # Updated to gemini-1.5-pro for higher reasoning accuracy as requested
            model = genai.GenerativeModel('gemini-1.5-pro') 
            
            prompt = "Analyze this Travel Ticket carefully. Return JSON list: [{\"date\": \"DD/MM/YYYY\", \"amount\": 500, \"km\": 0}]"
            response = model.generate_content([prompt, image_parts[0]])
            text = response.text.strip()
            if "```json" in text: text = text.split("```json")[1].split("```")[0]
            data = json.loads(text)
            results.extend(data if isinstance(data, list) else [data])
        except Exception as e:
            st.warning(f"Error reading {file.name}: {e}")
        progress_bar.progress((i + 1) / len(uploaded_files))
    progress_bar.empty()
    return results

def validate_against_rules(table_df, salary_file, rules_file):
    # Updated to gemini-1.5-pro for higher reasoning accuracy
    model = genai.GenerativeModel('gemini-1.5-pro')
    table_json = table_df.to_json(orient="records")
    
    salary_part = {
        "mime_type": salary_file.type,
        "data": salary_file.getvalue()
    }
    
    rules_part = {
        "mime_type": rules_file.type,
        "data": rules_file.getvalue()
    }

    prompt = f"""Audit this TA Claim Table against Salary Slip and Rules. Table: {table_json}. If OK, start with 'VALIDATED'."""
    
    response = model.generate_content([prompt, salary_part, rules_part])
    return response.text

# ==========================================
# 📥 SECTION 1: UPLOAD & SMART TABLE
# ==========================================
st.title("🧮 Step 2: TA Calculation (Logic Corrected)")

if 'final_tour_diary' not in st.session_state:
    st.error("⚠️ Please complete Step 1 (Tour Diary) first.")
    st.stop()

st.subheader("1. Smart Extract from Tickets")
ticket_files = st.file_uploader("Upload Tickets/Bills (PDF/Images)", accept_multiple_files=True, key="tick_up")

if ticket_files and st.button("🤖 Extract & Merge Ticket Data"):
    with st.spinner("Gemini Pro is reading tickets..."):
        st.session_state['extracted_tickets'] = extract_data_from_documents(ticket_files)
        if 'ta_rearranged_df' in st.session_state: del st.session_state['ta_rearranged_df']
        st.success("Tickets extracted! Merging into table...")
        st.rerun()

st.divider()

# Logic to generate table from diary
def smart_calculation_logic(row):
    mode = str(row.get("Mode_of_Travel", "")).lower()
    diary_date = str(row.get("Departure_Date", ""))
    
    # Defaults
    km = 0.0
    ticket_rate = 0.0
    rate_per_km = 0.0
    total_val = 0.0
    purpose = row.get("Purpose", "Official") 
    travel_class = "Express"

    # --- LOGIC SPLIT BASED ON MODE ---
    
    # CASE A: Public Transport (Train/Bus/Flight) -> Uses Col 9 & 10 ONLY
    if any(x in mode for x in ['rail', 'train', 'bus', 'flight', 'air']):
        travel_class = "2nd AC" if "rail" in mode or "train" in mode else "Economy" if "flight" in mode else "Express"
        
        # Try to find ticket price
        if 'extracted_tickets' in st.session_state:
            for t in st.session_state['extracted_tickets']:
                if str(t.get('date')) in diary_date or diary_date in str(t.get('date')):
                    ticket_rate = float(t.get('amount', 0))
                    break
        
        # COL 10 gets the value. COL 13 MUST BE ZERO.
        km = 0.0 
        rate_per_km = 0.0
        total_val = 0.0 

    # CASE B: Hired/Private Transport (Auto/Taxi) -> Uses Col 13 ONLY
    elif any(x in mode for x in ['auto', 'rickshaw', 'taxi', 'car', 'cab']):
        travel_class = "Road"
        ticket_rate = 0.0 # Col 9 & 10 must be zero
        
        # Get KM
        km = pd.to_numeric(row.get("KM", 0), errors='coerce')
        if pd.isna(km) or km == 0:
            km = try_get_km_from_raw(diary_date, row.get("Departure_Place", ""))
            
        # Set Rate
        rate_per_km = 12.0 if "auto" in mode else 16.0 
        
        # COL 13 gets the value. COL 10 MUST BE ZERO.
        total_val = km * rate_per_km

    return pd.Series([
        row.get("Departure_Place"), 
        row.get("Departure_Date"), 
        row.get("Departure_Time"), 
        row.get("Arrival_Place"), 
        row.get("Arrival_Date"), 
        row.get("Arrival_Time"), 
        row.get("Mode_of_Travel"), 
        travel_class, 
        ticket_rate,  # Col 9 (Ticket Price)
        ticket_rate,  # Col 10 (Actual Total Ticket)
        km,           # Col 11
        rate_per_km,  # Col 12
        total_val,    # Col 13 (Only for Auto/Taxi)
        purpose       # Col 18
    ])

if 'ta_rearranged_df' not in st.session_state:
    ta_df = st.session_state['final_tour_diary'].apply(smart_calculation_logic, axis=1)
    ta_df.columns = ALL_COLS
    st.session_state['ta_rearranged_df'] = ta_df

# ==========================================
# 🆕 SECTION 2: MANUAL PRICE/KM UPDATE
# ==========================================
st.subheader("2. Manual Update (Specific Journey)")
with st.expander("Click here to manually set Price or KM"):
    journey_options = st.session_state['ta_rearranged_df'].apply(
        lambda x: f"{x[COL2]} | {x[COL1]} to {x[COL4]}", axis=1
    ).tolist()
    
    col_sel, col_val, col_km = st.columns([2, 1, 1])
    
    selected_label = col_sel.selectbox("Select Journey", journey_options)
    new_price = col_val.number_input("Manual Ticket Price (Col 9)", min_value=0.0, step=10.0, key="man_pr")
    new_km = col_km.number_input("Manual KM (Col 11)", min_value=0.0, step=1.0, key="man_km")
    
    if st.button("✅ Apply Update"):
        idx = journey_options.index(selected_label)
        
        if new_price > 0:
            st.session_state['ta_rearranged_df'].at[idx, COL9] = new_price
            st.session_state['ta_rearranged_df'].at[idx, COL10] = new_price 
            st.session_state['ta_rearranged_df'].at[idx, COL13] = 0.0 # Force Col 13 to 0 if ticket exists
            
        if new_km > 0:
            st.session_state['ta_rearranged_df'].at[idx, COL11] = new_km
            # Recalculate Col 13 if KM is updated (assuming rate exists)
            rate = st.session_state['ta_rearranged_df'].at[idx, COL12]
            st.session_state['ta_rearranged_df'].at[idx, COL13] = new_km * rate
            st.session_state['ta_rearranged_df'].at[idx, COL10] = 0.0 # Force Col 10 to 0 if KM used
            
        st.success(f"Updated journey: {selected_label}")
        st.rerun()

# ==========================================
# 🧮 SECTION 3: REVIEW & EDIT TABLE
# ==========================================
st.subheader("3. Review & Edit TA Table")

df_to_edit = st.session_state['ta_rearranged_df'].copy()

# --- REAL-TIME CALCULATION LOGIC ---
# Ensure strict separation:
# If Col 9 (Ticket) > 0: Col 10 = Col 9, Col 13 = 0.
# Else: Col 10 = 0, Col 13 = Col 11 * Col 12.

# 1. Basic conversions
ticket_price = pd.to_numeric(df_to_edit[COL9], errors='coerce').fillna(0)
km = pd.to_numeric(df_to_edit[COL11], errors='coerce').fillna(0)
rate = pd.to_numeric(df_to_edit[COL12], errors='coerce').fillna(0)
taxi_calc = km * rate

# 2. Logic Application
# We use numpy where to vectorise the logic: If Ticket > 0, use Ticket for Col 10 and 0 for Col 13.
df_to_edit[COL10] = np.where(ticket_price > 0, ticket_price, 0.0)
df_to_edit[COL13] = np.where(ticket_price > 0, 0.0, taxi_calc)

# 3. Clean up Col 9 visual if it's meant to be 0 (optional, but keeps table clean)
df_to_edit[COL9] = np.where(ticket_price > 0, ticket_price, 0.0)

edited_ta = st.data_editor(
    df_to_edit,
    use_container_width=True,
    num_rows="dynamic",
    key="ta_editor_main",
    column_config={
        COL8: st.column_config.SelectboxColumn(COL8, options=["1st AC", "2nd AC", "3rd AC", "CC", "Sleeper", "Economy", "Express", "Road"]),
        COL9: st.column_config.NumberColumn(COL9, format="₹ %.2f"),
        COL10: st.column_config.NumberColumn(COL10, format="₹ %.2f", disabled=True, help="Ticket Amount Only"),
        COL11: st.column_config.NumberColumn(COL11, format="%.1f km"),
        COL12: st.column_config.NumberColumn(COL12, format="₹ %.2f"),
        COL13: st.column_config.NumberColumn(COL13, format="₹ %.2f", disabled=True, help="Road Mileage Amount Only"),
        COL18: st.column_config.TextColumn(COL18, width="medium")
    }
)

# SYNC BACK TO STATE WITH RECALCULATION
if COL9 in edited_ta.columns:
    # Re-apply the logic one last time on the edited data
    t_p = pd.to_numeric(edited_ta[COL9], errors='coerce').fillna(0)
    k_v = pd.to_numeric(edited_ta[COL11], errors='coerce').fillna(0)
    r_v = pd.to_numeric(edited_ta[COL12], errors='coerce').fillna(0)
    
    edited_ta[COL10] = np.where(t_p > 0, t_p, 0.0)
    edited_ta[COL13] = np.where(t_p > 0, 0.0, k_v * r_v)
    
    st.session_state['ta_rearranged_df'] = edited_ta

# Show Grand Totals
# The final claim is SUM(Col 10) + SUM(Col 13) because they are now mutually exclusive
total_ticket = edited_ta[COL10].sum()
total_mileage = edited_ta[COL13].sum()
grand_total = total_ticket + total_mileage

st.info(f"💡 Logic: If a Ticket Price exists (Col 10), Total (Col 13) is set to 0 to avoid double counting. If Ticket is 0, Col 13 shows KM amount.")

t_col1, t_col2, t_col3 = st.columns(3)
t_col1.metric("Train/Bus/Flight Total (Col 10)", f"₹ {total_ticket:.2f}")
t_col2.metric("Auto/Taxi Total (Col 13)", f"₹ {total_mileage:.2f}")
t_col3.metric("💰 Final Claim Amount", f"₹ {grand_total:.2f}")

# ==========================================
# 📑 SECTION 4: AI RULE VALIDATION
# ==========================================
st.divider()
st.subheader("4. AI Policy Validation (Rules & Salary Slip)")
col_a, col_b = st.columns(2)
with col_a: sal_up = st.file_uploader("Upload Salary Slip", type=['pdf','png','jpg'], key="salary_val")
with col_b: rules_up = st.file_uploader("Upload TA Rules", type=['pdf','txt'], key="rules_val")

if st.button("⚖️ Run AI Audit"):
    if not sal_up or not rules_up:
        st.error("Please upload both documents for validation.")
    else:
        with st.spinner("Validating with Gemini Pro..."):
            report = validate_against_rules(edited_ta, sal_up, rules_up)
            if "VALIDATED" in report.upper():
                st.success(report); st.session_state['audit_passed'] = True
            else:
                st.error("Policy Disparity Detected:"); st.info(report); st.session_state['audit_passed'] = False

if st.session_state.get('audit_passed'):
    if st.button("Proceed to DA Calculation ➡️"):
        st.switch_page("pages/3_DA_Calculation.py")
