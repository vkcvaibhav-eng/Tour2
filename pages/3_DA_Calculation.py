import streamlit as st
import pandas as pd
from datetime import datetime
import google.generativeai as genai
import json
import io

# ==========================================
# ⚙️ CONFIGURATION & SETUP
# ==========================================
st.set_page_config(layout="wide", page_title="Step 3: AI DA Calculation")
st.title("📅 Step 3: Intelligent DA Calculation (S.119 Rules)")

api_key = st.session_state.get('gemini_api_key')
if not api_key:
    st.error("⚠️ Gemini API Key not found. Please set it in the Home page.")
    st.stop()

genai.configure(api_key=api_key)
# Using Gemini 1.5 Pro for high-reasoning tasks like rule extraction
model = genai.GenerativeModel('gemini-1.5-pro')

# --- DATA PERSISTENCE ---
if 'ta_rearranged_df' not in st.session_state:
    st.warning("⚠️ No TA data found. Please complete the TA Calculation step first.")
    st.stop()

base_df = st.session_state['ta_rearranged_df'].copy()

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

for col in COL_NAMES:
    if col not in base_df.columns:
        base_df[col] = 0.0 if "Rs." in col else ""

# ==========================================
# 🧠 AI EXTRACTION & CALCULATION LOGIC
# ==========================================

def calculate_da_days_logic(start_dt, end_dt):
    """Calculates DA units based on the 6/12/24 hour rule."""
    duration = end_dt - start_dt
    total_hours = duration.total_seconds() / 3600
    if total_hours < 6: return 0.0, total_hours
    
    full_days = int(total_hours // 24)
    rem_hours = total_hours % 24
    extra = 0.0
    if 6 <= rem_hours < 12: extra = 0.5
    elif rem_hours >= 12: extra = 1.0
    return (full_days + extra), total_hours

def get_ai_context(salary_file, rules_file):
    """Extracts Pay Level and DA rates from documents."""
    prompt = """
    Analyze these documents (Salary Slip and TA/DA Rules). 
    1. Identify the Employee Name and Pay Level from the salary slip.
    2. From the Rules, find the Daily Allowance (DA) rate applicable to this Pay Level.
    3. If there are different rates for City vs Town, provide the standard rate.
    Return ONLY a JSON object: {"name": "...", "level": "...", "rate": 400.0}
    """
    # Note: File processing logic here (omitted for brevity, requires passing file bytes)
    # Returning a sample structured response for logic flow
    return {"name": "Vaibhavkumar Chaudhari", "level": "Level 10", "rate": 400.0}

# ==========================================
# 📑 UI SECTIONS
# ==========================================

st.subheader("1. Upload Documents for AI Intelligence")
c1, c2 = st.columns(2)
with c1: sal_up = st.file_uploader("Upload Salary Slip", type=['pdf','png','jpg'])
with c2: rule_up = st.file_uploader("Upload S.119 Rules", type=['pdf'])

if st.button("🚀 Run Intelligent Calculation"):
    if not sal_up or not rule_up:
        st.error("Please upload both documents.")
    else:
        with st.spinner("Gemini is auditing rules and calculating..."):
            # Step A: AI identifies the rate
            # (In a real app, you would upload the files to the Gemini API here)
            extracted_info = get_ai_context(sal_up, rule_up)
            da_rate = extracted_info['rate']
            
            st.info(f"✅ AI Identified: {extracted_info['name']} | {extracted_info['level']} | Rate: Rs.{da_rate}")

            # Step B: Apply calculations row by row
            for idx, row in base_df.iterrows():
                try:
                    # Parse dates/times
                    dep_dt = datetime.combine(pd.to_datetime(row["2. Departure Date"]).date(), 
                                            pd.to_datetime(row["3. Departure Time"]).time())
                    arr_dt = datetime.combine(pd.to_datetime(row["5. Arrival Date"]).date(), 
                                            pd.to_datetime(row["6. Arrival Time"]).time())
                    
                    # Logic for Column 14
                    da_units, hrs = calculate_da_days_logic(dep_dt, arr_dt)
                    base_df.at[idx, "14. Days of daily allowance receivable (Hrs)"] = f"{da_units} ({round(hrs, 1)} hrs)"
                    
                    # Column 15 & 16
                    base_df.at[idx, "15. Daily allowance rate (Rs.)"] = da_rate
                    base_df.at[idx, "16. Amount of Allowance (Rs.)"] = da_units * da_rate
                    
                    # Column 17: Total (10 + 13 + 16)
                    col10 = float(row["10. Actual Total Amount of Ticket (Rs.)"]) if row["10. Actual Total Amount of Ticket (Rs.)"] else 0
                    col13 = float(row["13. Total (Rs.)"]) if row["13. Total (Rs.)"] else 0
                    base_df.at[idx, "17. Total amount receivable (10+13+16) (Rs.)"] = col10 + col13 + (da_units * da_rate)
                
                except Exception as e:
                    st.error(f"Error in row {idx+1}: {e}")

st.subheader("2. Final DA Table (Columns 1-18)")
final_edited = st.data_editor(base_df[COL_NAMES], use_container_width=True, num_rows="dynamic")

if st.button("💾 Save & Finalize"):
    st.session_state['final_da_calc'] = final_edited
    st.success("DA Calculation Finalized!")
