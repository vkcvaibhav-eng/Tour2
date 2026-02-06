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
        except:
            return 0.0
    if isinstance(raw_data, list):
        for entry in raw_data:
            if entry.get('Departure Date') == dep_date and entry.get('Departure Place') == dep_place:
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
            prompt = "Analyze Travel Ticket. Return JSON: [{\"date\": \"DD/MM/YYYY\", \"amount\": 500, \"km\": 0}]"
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
    prompt = f"""
    Audit this TA Claim against Salary Slip and TA Rules.
    Claim Data: {table_json}
    Task: Validate Pay Level vs Travel Class and Auto Rates.
    If correct, start with 'VALIDATED'.
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
ticket_files = st.file_uploader("Upload Tickets/Bills", accept_multiple_files=True, key="tick_up")

if ticket_files and st.button("🤖 Extract & Merge Ticket Data"):
    st.session_state['extracted_tickets'] = extract_data_from_documents(ticket_files)
    if 'ta_rearranged_df' in st.session_state: del st.session_state['ta_rearranged_df']
    st.rerun()

st.divider()

# Logic to build the 13-column table
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
            if t.get('date') in diary_date or diary_date in str(t.get('date')):
                ticket_rate = float(t.get('amount', 0))
                break

    rate_per_km = 15.0 if ("auto" in mode or "rickshaw" in mode) else 0.0
    
    # Returning EXACT sequence of 13 Columns as requested
    return pd.Series([
        row.get("Departure_Place"),                 # 1
        row.get("Departure_Date"),                  # 2
        row.get("Departure_Time"),                  # 3
        row.get("Arrival_Place"),                   # 4
        row.get("Arrival_Date"),                    # 5
        row.get("Arrival_Time"),                    # 6
        row.get("Mode_of_Travel"),                  # 7
        travel_class,                               # 8
        ticket_rate,                                # 9
        ticket_rate,                                # 10
        km,                                         # 11
        rate_per_km,                                # 12
        0.0                                         # 13 (Calculated below)
    ])

if 'ta_rearranged_df' not in st.session_state:
    ta_df = st.session_state['final_tour_diary'].apply(smart_calculation_logic, axis=1)
    ta_df.columns = [
        "1. Departure Place", "2. Departure date", "3. Departure time", 
        "4. Arrival Place", "5. Arrival Date", "6. Arrival Time",
        "7. Mode", "8. Class", "9. Ticket price/rate (Rs.)", 
        "10. Actual Total Amount of Ticket (Rs.)", "11. KM", 
        "12. Rate (Rs.) (Auto/Vehicle)", "13. Total (Rs.)"
    ]
    st.session_state['ta_rearranged_df'] = ta_df

st.subheader("2. Review & Edit TA Table")

# Live Calculation logic to fix the KeyError
df_editor = st.session_state['ta_rearranged_df'].copy()

# Perform math before showing editor to ensure columns exist
df_editor["10. Actual Total Amount of Ticket (Rs.)"] = df_editor["9. Ticket price/rate (Rs.)"]
df_editor["13. Total (Rs.)"] = df_editor["10. Actual Total Amount of Ticket (Rs.)"] + (df_editor["11. KM"] * df_editor["12. Rate (Rs.) (Auto/Vehicle)"])

edited_ta = st.data_editor(
    df_editor,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "8. Class": st.column_config.SelectboxColumn("8. Class", options=["1st Class AC", "2nd Class AC", "3rd Class AC", "Sleeper", "Business Class", "Economy Class", "Bus Express", "Super Express"]),
        "13. Total (Rs.)": st.column_config.NumberColumn("13. Total", format="₹ %.2f", disabled=True)
    }
)

# Sync edits back to session state
st.session_state['ta_rearranged_df'] = edited_ta

# ==========================================
# 📑 SECTION 2: AI RULE VALIDATION
# ==========================================
st.divider()
st.subheader("3. AI Policy Validation (Rules & Salary Slip)")
col_a, col_b = st.columns(2)
with col_a: sal_up = st.file_uploader("Upload Salary Slip", type=['pdf','png','jpg'])
with col_b: rules_up = st.file_uploader("Upload TA Rules/Regulations", type=['pdf','txt'])

if st.button("⚖️ Run AI Audit"):
    if not sal_up or not rules_up:
        st.error("Please upload both documents.")
    else:
        with st.spinner("Analyzing rules..."):
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
