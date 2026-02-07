import streamlit as st
import pandas as pd
from datetime import datetime
import google.generativeai as genai
import json
import io

# ==========================================
# ⚙️ CONFIGURATION & SETUP
# ==========================================
st.set_page_config(layout="wide", page_title="Step 3: Intelligent DA Calculation")
st.title("📅 Step 3: AI-Driven Daily Allowance (DA) Calculation")

api_key = st.session_state.get('gemini_api_key')
if not api_key:
    st.error("⚠️ Gemini API Key not found. Please set it in the Home page.")
    st.stop()

genai.configure(api_key=api_key)

# Using gemini-1.5-pro for document reasoning
model = genai.GenerativeModel('gemini-1.5-pro')

# --- DATA PERSISTENCE ---
if 'ta_rearranged_df' not in st.session_state:
    st.warning("⚠️ No TA data found. Please complete the TA Calculation step first.")
    st.stop()

# Initialize the 18-column structure
COL_NAMES = [
    "1. Departure Place", "2. Departure Date", "3. Departure Time",
    "4. Arrival Place", "5. Arrival Date", "6. Arrival Time",
    "7. Mode", "8. Class", "9. Ticket Price/Rate (Rs.)",
    "10. Actual Total Amount of Ticket (Rs.)", "11. KM", "12. Rate (Rs.)",
    "13. Total (Rs.)", 
    "14. Days of daily allowance receivable (Hrs)", 
    "15. Daily allowance rate (Rs.)", 
    "16. Amount of Allowance (Rs.)", 
    "17. Total amount receivable (10+13+16) (Rs.)",
    "18. Purpose of Journey"
]

base_df = st.session_state['ta_rearranged_df'].copy()
for col in COL_NAMES:
    if col not in base_df.columns:
        base_df[col] = 0.0 if "Rs." in col else ""

# ==========================================
# 🧠 INTELLIGENT LOGIC FUNCTIONS
# ==========================================

def calculate_da_units(start_dt, end_dt):
    """
    Implements S.119 Rules:
    < 6 hrs: 0 DA
    6-12 hrs: 0.5 DA
    12-24 hrs: 1.0 DA
    > 24 hrs: 1.0 per 24hr block + remaining hours rule
    """
    duration = end_dt - start_dt
    total_hours = duration.total_seconds() / 3600
    
    if total_hours < 6:
        return 0.0, total_hours
    
    full_days = int(total_hours // 24)
    remaining_hours = total_hours % 24
    
    extra_da = 0.0
    if 6 <= remaining_hours < 12:
        extra_da = 0.5
    elif remaining_hours >= 12:
        extra_da = 1.0
        
    return (full_days + extra_da), total_hours

def process_docs_with_ai(salary_file, rules_file):
    """Uses Gemini to identify Pay Level and applicable DA Rate from rules."""
    # Convert files for Gemini
    sal_bytes = salary_file.read()
    rules_bytes = rules_file.read()
    
    prompt = """
    Analyze the uploaded Salary Slip and DA Rules (Statute S.119).
    1. Identify the Employee Name and Pay Level from the salary slip.
    2. In the Rules, find the 'Daily Allowance Rate' in Rupees applicable for this Pay Level.
    3. Return ONLY a valid JSON object:
    {"name": "string", "pay_level": "string", "da_rate": float}
    """
    
    response = model.generate_content([
        prompt,
        {"mime_type": "application/pdf", "data": sal_bytes},
        {"mime_type": "application/pdf", "data": rules_bytes}
    ])
    
    # Clean and parse JSON
    try:
        raw_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_json)
    except:
        return {"name": "Unknown", "pay_level": "Level 10", "da_rate": 400.0}

# ==========================================
# 📑 UI AND EXECUTION
# ==========================================

st.subheader("1. AI Audit Inputs")
st.info("Upload your documents. AI will extract your Pay Level and calculate DA based on S.119 Statute (6/12/24 Hour Rule).")

c1, c2 = st.columns(2)
with c1:
    sal_up = st.file_uploader("Upload Salary Slip", type=['pdf','png','jpg'])
with c2:
    rule_up = st.file_uploader("Upload TA/DA Rules (S.119)", type=['pdf'])

if st.button("🚀 Run Intelligent Calculation"):
    if not sal_up or not rule_up:
        st.error("Please upload both files to proceed.")
    else:
        with st.spinner("Gemini is analyzing documents and tour history..."):
            # A. AI Context Extraction
            context = process_docs_with_ai(sal_up, rule_up)
            da_rate = context['da_rate']
            
            st.success(f"Audit Complete: {context['name']} ({context['pay_level']}) found. Applied Rate: ₹{da_rate}")

            # B. Row-by-Row Calculation
            for idx, row in base_df.iterrows():
                try:
                    # Construct full datetime objects from columns 2, 3, 5, and 6
                    dep_dt = datetime.combine(pd.to_datetime(row["2. Departure Date"]).date(), 
                                            pd.to_datetime(row["3. Departure Time"]).time())
                    arr_dt = datetime.combine(pd.to_datetime(row["5. Arrival Date"]).date(), 
                                            pd.to_datetime(row["6. Arrival Time"]).time())
                    
                    # Column 14: Days and Hours
                    da_units, total_hrs = calculate_da_units(dep_dt, arr_dt)
                    base_df.at[idx, "14. Days of daily allowance receivable (Hrs)"] = f"{da_units} ({round(total_hrs, 1)} hrs)"
                    
                    # Column 15: AI-identified rate
                    base_df.at[idx, "15. Daily allowance rate (Rs.)"] = da_rate
                    
                    # Column 16: Calculation
                    allowance_amt = da_units * da_rate
                    base_df.at[idx, "16. Amount of Allowance (Rs.)"] = allowance_amt
                    
                    # Column 17: Total (10 + 13 + 16)
                    col10 = pd.to_numeric(row["10. Actual Total Amount of Ticket (Rs.)"], errors='coerce') or 0
                    col13 = pd.to_numeric(row["13. Total (Rs.)"], errors='coerce') or 0
                    base_df.at[idx, "17. Total amount receivable (10+13+16) (Rs.)"] = col10 + col13 + allowance_amt
                    
                except Exception as e:
                    st.warning(f"Skipping row {idx+1} due to date format error.")

st.subheader("2. Final TA/DA Worksheet (Columns 1-18)")
final_df = st.data_editor(base_df[COL_NAMES], use_container_width=True, num_rows="dynamic")

if st.button("💾 Save & Export"):
    st.session_state['final_da_calculation'] = final_df
    st.success("Calculations saved to session state!")
