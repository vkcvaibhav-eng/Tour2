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
            
            # Use Gemini 1.5 Pro for high accuracy in reading Mode/Class from receipts
            model = genai.GenerativeModel('gemini-1.5-pro') 
            
            # UPGRADED PROMPT: Specifically asks for Mode and Class to map correctly
            prompt = """
            Analyze this Travel Ticket/Bill. Extract the following details accurately:
            1. Date (DD/MM/YYYY)
            2. Mode (Train, Bus, Flight, Auto, Taxi, Car)
            3. Class (e.g., 2nd AC, Sleeper, General, Economy, or 'Road' for taxi)
            4. Total Amount (Price)
            5. KM (if mentioned on taxi bill)
            
            Return ONLY a valid JSON list like this: 
            [{"date": "12/03/2024", "mode": "Bus", "class": "Sleeper", "amount": 1200, "km": 0}]
            """
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
    model = genai.GenerativeModel('gemini-1.5-pro')
    table_json = table_df.to_json(orient="records")
    
    salary_part = { "mime_type": salary_file.type, "data": salary_file.getvalue() }
    rules_part = { "mime_type": rules_file.type, "data": rules_file.getvalue() }

    prompt = f"""Audit this TA Claim Table against Salary Slip and Rules. Table: {table_json}. If OK, start with 'VALIDATED'."""
    response = model.generate_content([prompt, salary_part, rules_part])
    return response.text

# ==========================================
# 📥 SECTION 1: UPLOAD & SMART TABLE
# ==========================================
st.title("🧮 Step 2: TA Calculation (Smart Mode Mapping)")

if 'final_tour_diary' not in st.session_state:
    st.error("⚠️ Please complete Step 1 (Tour Diary) first.")
    st.stop()

st.subheader("1. Smart Extract from Tickets")
ticket_files = st.file_uploader("Upload Tickets/Bills (PDF/Images)", accept_multiple_files=True, key="tick_up")

if ticket_files and st.button("🤖 Extract & Merge Ticket Data"):
    with st.spinner("Gemini Pro is reading tickets..."):
        st.session_state['extracted_tickets'] = extract_data_from_documents(ticket_files)
        # Clear previous table to force re-calculation with new data
        if 'ta_rearranged_df' in st.session_state: del st.session_state['ta_rearranged_df']
        st.success("Tickets extracted! Merging into table...")
        st.rerun()

st.divider()

# Logic to generate table from diary
def smart_calculation_logic(row):
    # 1. Start with Diary defaults
    diary_mode = str(row.get("Mode_of_Travel", "")).lower()
    diary_date = str(row.get("Departure_Date", ""))
    
    # 2. Check for AI Extracted Ticket Match
    ticket_data = None
    if 'extracted_tickets' in st.session_state:
        for t in st.session_state['extracted_tickets']:
            # Flexible date matching
            t_date = str(t.get('date', ''))
            if t_date and (t_date in diary_date or diary_date in t_date):
                ticket_data = t
                break
    
    # 3. Determine Mode & Class (Prioritize Ticket Data if found)
    final_mode = diary_mode
    final_class = "Express"
    ticket_amount = 0.0
    km_extracted = 0.0
    
    if ticket_data:
        # If ticket has a mode (e.g., "Bus", "Taxi"), overwrite the diary mode
        if ticket_data.get('mode'):
            final_mode = str(ticket_data.get('mode')).lower()
        
        if ticket_data.get('class'):
            final_class = str(ticket_data.get('class'))
            
        ticket_amount = float(ticket_data.get('amount', 0))
        km_extracted = float(ticket_data.get('km', 0))
    else:
        # Fallback Logic if no ticket matched
        if "rail" in final_mode or "train" in final_mode: final_class = "2nd AC"
        elif "flight" in final_mode: final_class = "Economy"
        elif "auto" in final_mode or "taxi" in final_mode: final_class = "Road"

    # 4. Fill Columns based on Final Mode
    # --- Public Transport (Train/Bus/Flight) ---
    if any(x in final_mode for x in ['rail', 'train', 'bus', 'flight', 'air', 'metro']):
        col9_price = ticket_amount
        col10_total = ticket_amount
        col11_km = 0.0
        col12_rate = 0.0
        col13_total = 0.0
        
    # --- Private Transport (Auto/Taxi/Car) ---
    elif any(x in final_mode for x in ['auto', 'rickshaw', 'taxi', 'car', 'cab', 'road']):
        col9_price = 0.0
        col10_total = 0.0
        
        # Use KM from ticket if available, else from diary
        col11_km = km_extracted if km_extracted > 0 else pd.to_numeric(row.get("KM", 0), errors='coerce')
        if pd.isna(col11_km): col11_km = 0.0
        
        # Determine Rate
        col12_rate = 12.0 if "auto" in final_mode else 16.0 
        
        # Calculate Total immediately
        col13_total = col11_km * col12_rate
    else:
        # Fallback
        col9_price, col10_total, col11_km, col12_rate, col13_total = 0.0, 0.0, 0.0, 0.0, 0.0

    return pd.Series([
        row.get("Departure_Place"), 
        row.get("Departure_Date"), 
        row.get("Departure_Time"), 
        row.get("Arrival_Place"), 
        row.get("Arrival_Date"), 
        row.get("Arrival_Time"), 
        final_mode.title(), # Col 7
        final_class,        # Col 8
        col9_price,         # Col 9
        col10_total,        # Col 10
        col11_km,           # Col 11
        col12_rate,         # Col 12
        col13_total,        # Col 13
        row.get("Purpose", "Official") # Col 18
    ])

if 'ta_rearranged_df' not in st.session_state:
    ta_df = st.session_state['final_tour_diary'].apply(smart_calculation_logic, axis=1)
    ta_df.columns = ALL_COLS
    st.session_state['ta_rearranged_df'] = ta_df

# ==========================================
# 🆕 SECTION 2: MANUAL PRICE/KM UPDATE
# ==========================================
st.subheader("2. Manual Update (Specific Journey)")
st.info("ℹ️ Select a journey to update Ticket Price OR Distance parameters.")

# Ensure we have a persistent key for the selection to avoid resetting
if "selected_journey_index" not in st.session_state:
    st.session_state["selected_journey_index"] = 0

with st.expander("Click here to manually set Price, KM, or Rate", expanded=True):
    journey_options = st.session_state['ta_rearranged_df'].apply(
        lambda x: f"{x[COL2]} | {x[COL1]} to {x[COL4]} ({x[COL7]})", axis=1
    ).tolist()
    
    col_sel, col_pr, col_km, col_rt = st.columns([3, 1, 1, 1])
    
    selected_label = col_sel.selectbox("Select Journey to Update", journey_options, index=st.session_state["selected_journey_index"])
    
    # Get current index
    current_idx = journey_options.index(selected_label)
    st.session_state["selected_journey_index"] = current_idx # Keep selection stable

    new_price = col_pr.number_input("Ticket Price (Col 9)", min_value=0.0, step=10.0, key="man_pr")
    new_km = col_km.number_input("Distance KM (Col 11)", min_value=0.0, step=1.0, key="man_km")
    new_rate = col_rt.number_input("Rate/KM (Col 12)", min_value=0.0, step=1.0, key="man_rt")
    
    if st.button("✅ Update & Recalculate"):
        # Logic: 
        # 1. If Price is entered -> Clear KM/Rate totals, Set Ticket Totals.
        # 2. If KM or Rate is entered -> Clear Ticket Totals, Set KM*Rate Totals.
        
        if new_price > 0:
            st.session_state['ta_rearranged_df'].at[current_idx, COL9] = new_price
            st.session_state['ta_rearranged_df'].at[current_idx, COL10] = new_price 
            st.session_state['ta_rearranged_df'].at[current_idx, COL13] = 0.0
            st.session_state['ta_rearranged_df'].at[current_idx, COL11] = 0.0 # Clear KM
            st.session_state['ta_rearranged_df'].at[current_idx, COL12] = 0.0 # Clear Rate
            st.success(f"Updated Ticket Price to ₹{new_price} for {selected_label}")
            
        elif new_km > 0 or new_rate > 0:
            # If user enters KM but not rate, try to keep existing rate, else default 12
            current_rate = st.session_state['ta_rearranged_df'].at[current_idx, COL12]
            final_rate = new_rate if new_rate > 0 else (current_rate if current_rate > 0 else 12.0)
            
            # If user enters Rate but not KM, keep existing KM
            current_km = st.session_state['ta_rearranged_df'].at[current_idx, COL11]
            final_km = new_km if new_km > 0 else current_km
            
            total_calc = final_km * final_rate
            
            st.session_state['ta_rearranged_df'].at[current_idx, COL11] = final_km
            st.session_state['ta_rearranged_df'].at[current_idx, COL12] = final_rate
            st.session_state['ta_rearranged_df'].at[current_idx, COL13] = total_calc
            st.session_state['ta_rearranged_df'].at[current_idx, COL9] = 0.0 # Clear Ticket
            st.session_state['ta_rearranged_df'].at[current_idx, COL10] = 0.0 # Clear Ticket Total
            
            st.success(f"Updated: {final_km} km @ ₹{final_rate}/km = ₹{total_calc}")
            
        st.rerun()

# ==========================================
# 🧮 SECTION 3: REVIEW & EDIT TABLE
# ==========================================
st.subheader("3. Review & Edit TA Table")

df_to_edit = st.session_state['ta_rearranged_df'].copy()

# --- REAL-TIME CALCULATION LOGIC (Safety Check) ---
ticket_price = pd.to_numeric(df_to_edit[COL9], errors='coerce').fillna(0)
km = pd.to_numeric(df_to_edit[COL11], errors='coerce').fillna(0)
rate = pd.to_numeric(df_to_edit[COL12], errors='coerce').fillna(0)

# If Ticket Price exists -> Ticket Total = Price, Road Total = 0
# Else -> Ticket Total = 0, Road Total = KM * Rate
df_to_edit[COL10] = np.where(ticket_price > 0, ticket_price, 0.0)
df_to_edit[COL13] = np.where(ticket_price > 0, 0.0, km * rate)

edited_ta = st.data_editor(
    df_to_edit,
    use_container_width=True,
    num_rows="dynamic",
    key="ta_editor_main",
    column_config={
        COL8: st.column_config.SelectboxColumn(COL8, options=["1st AC", "2nd AC", "3rd AC", "CC", "Sleeper", "Economy", "Express", "Road"]),
        COL9: st.column_config.NumberColumn(COL9, format="₹ %.2f", help="Enter Ticket Price here"),
        COL10: st.column_config.NumberColumn(COL10, format="₹ %.2f", disabled=True, help="Calculated Ticket Amount"),
        COL11: st.column_config.NumberColumn(COL11, format="%.1f km", help="Enter Distance here"),
        COL12: st.column_config.NumberColumn(COL12, format="₹ %.2f", help="Enter Rate per KM here"),
        COL13: st.column_config.NumberColumn(COL13, format="₹ %.2f", disabled=True, help="Calculated Road Amount"),
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
total_ticket = edited_ta[COL10].sum()
total_mileage = edited_ta[COL13].sum()
grand_total = total_ticket + total_mileage

st.info(f"💡 Calculation Logic: Ticket Price (Col 9) takes priority. If Ticket Price is 0, system calculates Distance (Col 11) × Rate (Col 12).")

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
