import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
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

ALL_COLS = [COL1, COL2, COL3, COL4, COL5, COL6, COL7, COL8, COL9, COL10, COL11, COL12, COL13]

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
            prompt = "Analyze Travel Ticket. Return JSON list: [{\"date\": \"DD/MM/YYYY\", \"amount\": 500, \"km\": 0}]"
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content([prompt, image_parts[0]])
            text = response.text.strip()
            if "```json" in text: text = text.split("```json")[1].split("```")[0]
            data = json.loads(text)
            results.extend(data if isinstance(data, list) else [data])
        except: pass
        progress_bar.progress((i + 1) / len(uploaded_files))
    progress_bar.empty()
    return results

def validate_against_rules(table_df, salary_file, rules_file):
    model = genai.GenerativeModel('gemini-1.5-flash')
    table_json = table_df.to_json(orient="records")
    prompt = f"""Audit this TA Claim: {table_json}. Compare with Salary and Rules. Start with 'VALIDATED' if OK."""
    response = model.generate_content([prompt, salary_file, rules_file])
    return response.text

# ==========================================
# 📥 SECTION 1: UPLOAD & TABLE
# ==========================================
st.title("🧮 Step 2: TA Calculation (Rearranged 1-13)")

if 'final_tour_diary' not in st.session_state:
    st.error("⚠️ Please complete Step 1 (Tour Diary) first.")
    st.stop()

st.subheader("1. Smart Extract from Tickets")
ticket_files = st.file_uploader("Upload Tickets/Bills", accept_multiple_files=True, key="tick_up")

if ticket_files and st.button("🤖 Extract & Merge Ticket Data"):
    with st.spinner("Reading tickets..."):
        st.session_state['extracted_tickets'] = extract_data_from_documents(ticket_files)
        if 'ta_rearranged_df' in st.session_state: del st.session_state['ta_rearranged_df']
        st.success("Tickets extracted!")
        st.rerun()

st.divider()

def smart_calculation_logic(row):
    mode = str(row.get("Mode_of_Travel", "")).lower()
    diary_date = str(row.get("Departure_Date", ""))
    km = pd.to_numeric(row.get("KM", 0), errors='coerce')
    if pd.isna(km) or km == 0:
        km = try_get_km_from_raw(diary_date, row.get("Departure_Place", ""))
    
    ticket_rate = 0.0
    travel_class = "2nd AC" if "rail" in mode else "Economy" if "flight" in mode else "Express"
    
    if 'extracted_tickets' in st.session_state:
        for t in st.session_state['extracted_tickets']:
            if str(t.get('date')) in diary_date or diary_date in str(t.get('date')):
                ticket_rate = float(t.get('amount', 0))
                break

    rate_per_km = 15.0 if ("auto" in mode or "rickshaw" in mode) else 0.0
    return pd.Series([
        row.get("Departure_Place"), row.get("Departure_Date"), row.get("Departure_Time"),
        row.get("Arrival_Place"), row.get("Arrival_Date"), row.get("Arrival_Time"),
        row.get("Mode_of_Travel"), travel_class, ticket_rate, ticket_rate, km, rate_per_km, 0.0
    ])

# Ensure state is initialized with correct columns
if 'ta_rearranged_df' not in st.session_state:
    df_base = st.session_state['final_tour_diary'].apply(smart_calculation_logic, axis=1)
    df_base.columns = ALL_COLS
    st.session_state['ta_rearranged_df'] = df_base

st.subheader("2. Review & Edit TA Table")

# Important: We re-calculate before showing to avoid KeyError on the first run
temp_df = st.session_state['ta_rearranged_df'].copy()
temp_df[COL10] = pd.to_numeric(temp_df[COL9], errors='coerce').fillna(0)
temp_df[COL13] = temp_df[COL10] + (pd.to_numeric(temp_df[COL11], errors='coerce').fillna(0) * pd.to_numeric(temp_df[COL12], errors='coerce').fillna(0))

edited_ta = st.data_editor(
    temp_df,
    use_container_width=True,
    num_rows="dynamic",
    key="ta_editor_v2",
    column_config={
        COL8: st.column_config.SelectboxColumn(COL8, options=["1st AC", "2nd AC", "3rd AC", "CC", "Business Class", "Economic Class", "Express"]),
        COL10: st.column_config.NumberColumn(COL10, format="₹ %.2f", disabled=True),
        COL13: st.column_config.NumberColumn(COL13, format="₹ %.2f", disabled=True)
    }
)

# Re-run calculations on the edited data to keep totals live
edited_ta[COL10] = pd.to_numeric(edited_ta[COL9], errors='coerce').fillna(0)
edited_ta[COL13] = edited_ta[COL10] + (pd.to_numeric(edited_ta[COL11], errors='coerce').fillna(0) * pd.to_numeric(edited_ta[COL12], errors='coerce').fillna(0))
st.session_state['ta_rearranged_df'] = edited_ta

# ==========================================
# 📑 SECTION 2: AI RULE VALIDATION
# ==========================================
st.divider()
st.subheader("3. AI Policy Validation")
col_a, col_b = st.columns(2)
with col_a: sal_up = st.file_uploader("Upload Salary Slip", type=['pdf','png','jpg'], key="sal_auth")
with col_b: rules_up = st.file_uploader("Upload TA Rules", type=['pdf','txt'], key="rule_auth")

if st.button("⚖️ Run AI Audit"):
    if not sal_up or not rules_up:
        st.error("Please upload both documents.")
    else:
        with st.spinner("Analyzing policy..."):
            report = validate_against_rules(edited_ta, sal_up, rules_up)
            if "VALIDATED" in report.upper():
                st.success(report)
                st.session_state['audit_passed'] = True
            else:
                st.error("Disparity Found:")
                st.info(report)
                st.session_state['audit_passed'] = False

if st.session_state.get('audit_passed'):
    if st.button("Proceed to DA Calculation ➡️"):
        st.switch_page("pages/3_DA_Calculation.py")
