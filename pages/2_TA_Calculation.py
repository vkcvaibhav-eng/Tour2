import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import io
from PIL import Image

# ==========================================
# ⚙️ CONFIGURATION & SETUP
# ==========================================
st.set_page_config(layout="wide", page_title="Step 2: TA Calculation (AI + Manual)")

api_key = st.session_state.get('gemini_api_key')
if not api_key:
    st.error("⚠️ Gemini API Key not found. Please set it in the Home page.")
    st.stop()

genai.configure(api_key=api_key)

# ==========================================
# 🧠 HELPER: RETRIEVE MISSING KM FROM RAW DATA
# ==========================================
def try_get_km_from_raw(dep_date, dep_place):
    """
    Looks back at the raw Gemini JSON from the previous step to find 'KM' 
    if it was lost during the editing process.
    """
    raw_data = st.session_state.get('extracted_data', {})
    
    # Parse JSON if it's stored as a string
    if isinstance(raw_data, str):
        try:
            if "```json" in raw_data:
                raw_data = json.loads(raw_data.split("```json")[1].split("```")[0])
            elif "```" in raw_data:
                raw_data = json.loads(raw_data.split("```")[1].split("```")[0])
        except:
            return 0.0

    # Search for matching entry
    if isinstance(raw_data, list):
        for entry in raw_data:
            if entry.get('Departure Date') == dep_date and entry.get('Departure Place') == dep_place:
                return float(entry.get('KM', 0))
    return 0.0

# ==========================================
# 🧠 AI ENGINE: DOCUMENT EXTRACTION
# ==========================================
def extract_data_from_documents(uploaded_files, doc_type="ticket"):
    if not uploaded_files: return []
    results = []
    progress_bar = st.progress(0)
    
    for i, file in enumerate(uploaded_files):
        try:
            image_data = file.getvalue()
            image_parts = [{"mime_type": file.type, "data": image_data}]
            
            if doc_type == "salary":
                prompt = "Analyze this Salary Slip. Return JSON: {\"basic_pay\": 12345, \"pay_level\": \"Level 11\"}"
            else:
                prompt = "Analyze this Travel Ticket. Return JSON: [{\"date\": \"DD/MM/YYYY\", \"mode\": \"Bus\", \"amount\": 540, \"km\": 0}]"

            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content([prompt, image_parts[0]])
            
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            
            data = json.loads(text)
            if isinstance(data, list): results.extend(data)
            else: results.append(data)
                
        except Exception as e:
            st.warning(f"Could not read file {file.name}: {e}")
        progress_bar.progress((i + 1) / len(uploaded_files))
        
    progress_bar.empty()
    return results

# ==========================================
# 📥 SECTION 1: UPLOADS & INTELLIGENCE
# ==========================================
st.title("🧮 Step 2: TA Calculation (Smart Extract)")
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Upload Salary Slip")
    salary_file = st.file_uploader("For Pay Level Validation", type=['png', 'jpg', 'jpeg', 'pdf'], key="sal_up")
    if salary_file and st.button("🔍 Analyze Salary Slip"):
        data = extract_data_from_documents([salary_file], "salary")
        if data:
            st.session_state['user_salary_info'] = data[0]
            st.success("Salary data extracted.")

with col2:
    st.subheader("2. Upload Tickets / Bills")
    ticket_files = st.file_uploader("Upload Bills", accept_multiple_files=True, type=['png', 'jpg', 'jpeg', 'pdf'], key="tick_up")
    if ticket_files and st.button("🤖 Extract Ticket Data"):
        extracted_tickets = extract_data_from_documents(ticket_files, "ticket")
        st.session_state['extracted_tickets'] = extracted_tickets
        st.success(f"Extracted {len(extracted_tickets)} tickets!")

st.divider()

# ==========================================
# 🗓️ SECTION 2: THE UPDATED CALCULATOR
# ==========================================
st.header("3. Review & Edit Calculations")

if 'final_tour_diary' not in st.session_state:
    st.error("⚠️ Please complete Step 1 (Tour Diary) first.")
    st.stop()

df = st.session_state['final_tour_diary'].copy()

def smart_prefill(row):
    mode = str(row.get("Mode of Travel", "")).lower()
    diary_date = str(row.get("Departure Date", ""))
    dep_place = row.get("Departure Place", "")
    
    # 1. Start with Diary KM
    km = pd.to_numeric(row.get("KM", 0), errors='coerce')
    if pd.isna(km) or km == 0:
        # FEATURE ADDED: Try to recover missing KM from raw data
        km = try_get_km_from_raw(diary_date, dep_place)
    
    class_travel = "Other"
    ticket_price = 0.0
    rate_per_km = 0.0
    
    # Mode Detection
    if "private" in mode or "car" in mode: class_travel = "Own Car / Pvt"
    elif "bus" in mode: class_travel = "Bus / ST"
    elif "rail" in mode or "train" in mode: class_travel = "Rail"
    
    # Merge Extracted Ticket Data
    if 'extracted_tickets' in st.session_state:
        for t in st.session_state['extracted_tickets']:
            if t.get('date') in diary_date or diary_date in t.get('date', ''):
                ticket_price = float(t.get('amount', 0))
                if t.get('km', 0) > 0: km = float(t.get('km'))
                break
    
    actual_total = ticket_price
    mileage_total = km * rate_per_km

    return pd.Series([class_travel, ticket_price, actual_total, km, rate_per_km, mileage_total])

if 'ta_calculation_df' not in st.session_state:
    processed_cols = df.apply(smart_prefill, axis=1)
    processed_cols.columns = ["Class_of_Travel", "Ticket_Price_Rate", "Actual_Ticket_Amount", "Kilometer", "Rate_per_KM", "Mileage_Total"]
    st.session_state['ta_calculation_df'] = pd.concat([df, processed_cols], axis=1)

if st.button("🔄 Reload & Merge Extracted Data"):
    del st.session_state['ta_calculation_df']
    st.rerun()

# 4. Data Editor & Live Calculations
edited_ta = st.data_editor(
    st.session_state['ta_calculation_df'],
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "Kilometer": st.column_config.NumberColumn("11. KM", format="%.1f km"),
        "Mileage_Total": st.column_config.NumberColumn("13. Total (Mileage)", format="₹ %.2f", disabled=True)
    }
)

# Recalculate totals
edited_ta["Mileage_Total"] = edited_ta["Kilometer"] * edited_ta["Rate_per_KM"]
st.session_state['ta_calculation_df'] = edited_ta

# Display Metrics
total_ticket = edited_ta["Actual_Ticket_Amount"].sum()
total_mileage = edited_ta["Mileage_Total"].sum()
st.metric("💰 GRAND TOTAL", f"₹ {total_ticket + total_mileage:,.2f}")
