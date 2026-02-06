import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import io
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

# ==========================================
# 🧠 HELPER: RETRIEVE MISSING KM FROM RAW DATA
# ==========================================
def try_get_km_from_raw(dep_date, dep_place):
    raw_data = st.session_state.get('extracted_data', {})
    if isinstance(raw_data, str):
        try:
            if "```json" in raw_data:
                raw_data = json.loads(raw_data.split("```json")[1].split("```")[0])
            elif "```" in raw_data:
                raw_data = json.loads(raw_data.split("```")[1].split("```")[0])
        except:
            return 0.0

    if isinstance(raw_data, list):
        for entry in raw_data:
            if str(entry.get('Departure Date')) == str(dep_date) and entry.get('Departure Place') == dep_place:
                return float(entry.get('KM', 0))
    return 0.0

# ==========================================
# 🧠 AI ENGINE: DOCUMENT EXTRACTION & VALIDATION
# ==========================================
def extract_data_from_documents(uploaded_files):
    if not uploaded_files: return []
    results = []
    progress_bar = st.progress(0)
    for i, file in enumerate(uploaded_files):
        try:
            image_data = file.getvalue()
            image_parts = [{"mime_type": file.type, "data": image_data}]
            prompt = "Analyze this Travel Ticket. Return JSON list: [{\"date\": \"DD/MM/YYYY\", \"mode\": \"Bus/Rail\", \"amount\": 500, \"km\": 0}]"
            model = genai.GenerativeModel('gemini-1.5-flash')
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
    model = genai.GenerativeModel('gemini-1.5-flash')
    table_json = table_df.to_json(orient="records")
    
    prompt = f"""
    You are a TA Audit Expert. Compare this TA Claim Table with the uploaded Salary Slip and TA Rules.
    
    Claim Table Data: {table_json}
    
    TASKS:
    1. Identify the user's Pay Level/Grade from the Salary Slip.
    2. Check TA Rules: Is the 'Class' (Col 8) allowed for this Pay Level? 
    3. Check 'Rate' (Col 12): Does it match the Auto/Taxi rate in the rules?
    
    If everything is correct, start with 'VALIDATED'. Otherwise, list each disparity clearly.
    """
    response = model.generate_content([prompt, salary_file, rules_file])
    return response.text

# ==========================================
# 📥 SECTION 1: UPLOAD & SMART TABLE
# ==========================================
st.title("🧮 Step 2: TA Calculation (Rearranged 1-13)")

if 'final_tour_diary' not in st.session_state:
    st.error("⚠️ Please complete Step 1 (Tour Diary) first.")
    st.stop()

st.subheader("1. Smart Extract from Tickets")
ticket_files = st.file_uploader("Upload Tickets/Bills (PDF/Images)", accept_multiple_files=True, key="tick_up")

if ticket_files and st.button("🤖 Extract & Merge Ticket Data"):
    with st.spinner("Gemini is reading tickets..."):
        st.session_state['extracted_tickets'] = extract_data_from_documents(ticket_files)
        if 'ta_rearranged_df' in st.session_state: del st.session_state['ta_rearranged_df']
        st.success("Tickets extracted! Merging into table below...")
        st.rerun()

st.divider()

# DEFINING THE EXACT COLUMN NAMES TO PREVENT KEYERROR
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

def smart_calculation_logic(row):
    mode = str(row.get("Mode_of_Travel", "")).lower()
    diary_date = str(row.get("Departure_Date", ""))
    
    km = pd.to_numeric(row.get("KM", 0), errors='coerce')
    if pd.isna(km) or km == 0:
        km = try_get_km_from_raw(diary_date, row.get("Departure_Place", ""))

    ticket_rate = 0.0
    # Auto-detect class
    travel_class = "2nd AC" if "rail" in mode else "Economy" if "flight" in mode else "Express"
    
    if 'extracted_tickets' in st.session_state:
        for t in st.session_state['extracted_tickets']:
            if str(t.get('date')) in diary_date or diary_date in str(t.get('date')):
                ticket_rate = float(t.get('amount', 0))
                if t.get('km', 0) > 0: km = float(t.get('km'))
                break

    rate_per_km = 0.0
    if "auto" in mode or "rickshaw" in mode:
        rate_per_km = 15.0 # Default, user can edit
    
    return pd.Series([
        row.get("Departure_Place"), row.get("Departure_Date"), row.get("Departure_Time"),
        row.get("Arrival_Place"), row.get("Arrival_Date"), row.get("Arrival_Time"),
        row.get("Mode_of_Travel"), travel_class, ticket_rate, ticket_rate, km, rate_per_km, 0.0
    ])

if 'ta_rearranged_df' not in st.session_state:
    ta_df = st.session_state['final_tour_diary'].apply(smart_calculation_logic, axis=1)
    ta_df.columns = [COL1, COL2, COL3, COL4, COL5, COL6, COL7, COL8, COL9, COL10, COL11, COL12, COL13]
    st.session_state['ta_rearranged_df'] = ta_df

st.subheader("2. Review & Edit TA Table")

edited_ta = st.data_editor(
    st.session_state['ta_rearranged_df'],
    use_container_width=True,
    num_rows="dynamic",
    key="ta_editor_main",
    column_config={
        COL8: st.column_config.SelectboxColumn(
            COL8, 
            options=["1st AC", "2nd AC", "3rd AC", "CC", "Sleeper", "Business Class", "Economic Class", "Express", "Super Express"]
        ),
        COL10: st.column_config.NumberColumn(COL10, format="₹ %.2f", disabled=True),
        COL13: st.column_config.NumberColumn(COL13, format="₹ %.2f", disabled=True)
    }
)

# Create a copy to ensure we aren't working on a fragmented view
df_final = edited_ta.copy()

# Ensure the column exists before calling it (The Fix for KeyError)
if COL9 in df_final.columns:
    # Use to_numeric to prevent errors if the user typed text in a number box
    df_final[COL10] = pd.to_numeric(df_final[COL9], errors='coerce').fillna(0)
    
    # Calculate Total safely
    km = pd.to_numeric(df_final[COL11], errors='coerce').fillna(0)
    rate = pd.to_numeric(df_final[COL12], errors='coerce').fillna(0)
    df_final[COL13] = df_final[COL10] + (km * rate)
    
    # Update the session state with the calculated values
    st.session_state['ta_rearranged_df'] = df_final
else:
    # If for some reason the column is missing, force a reset
    st.warning("Table columns out of sync. Resetting...")
    del st.session_state['ta_rearranged_df']
    st.rerun()# FIXED CALCULATION LOGIC (Using the variables to ensure names match)
edited_ta[COL10] = edited_ta[COL9]
edited_ta[COL13] = edited_ta[COL10] + (edited_ta[COL11] * edited_ta[COL12])
st.session_state['ta_rearranged_df'] = edited_ta

# ==========================================
# 📑 SECTION 2: AI RULE VALIDATION
# ==========================================
st.divider()
st.subheader("3. AI Policy Validation (Rules & Salary Slip)")
col_a, col_b = st.columns(2)
with col_a: sal_up = st.file_uploader("Upload Salary Slip", type=['pdf','png','jpg'], key="salary_val")
with col_b: rules_up = st.file_uploader("Upload TA Rules/Regulations", type=['pdf','txt'], key="rules_val")

if st.button("⚖️ Run AI Audit"):
    if not sal_up or not rules_up:
        st.error("Please upload both documents for validation.")
    else:
        with st.spinner("Gemini is validating your claim against company policy..."):
            report = validate_against_rules(edited_ta, sal_up, rules_up)
            
            if "VALIDATED" in report.upper():
                st.success(report)
                st.session_state['audit_passed'] = True
            else:
                st.error("Policy Disparity Detected:")
                st.info(report)
                st.session_state['audit_passed'] = False

if st.session_state.get('audit_passed'):
    if st.button("Proceed to DA Calculation ➡️"):
        st.switch_page("pages/3_DA_Calculation.py")

