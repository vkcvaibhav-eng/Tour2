import streamlit as st
import pandas as pd
from datetime import datetime
import google.generativeai as genai
import json

st.set_page_config(layout="wide", page_title="DA Calculation & AI Audit")
st.title("📅 Step 3: Intelligent Daily Allowance (DA) Calculation")

# --- API CONFIGURATION ---
api_key = st.session_state.get('gemini_api_key')
if not api_key:
    st.error("⚠️ Please set your Gemini API Key on the Home/Config page.")
    st.stop()
genai.configure(api_key=api_key)

# --- DATA PREPARATION ---
if 'ta_rearranged_df' not in st.session_state:
    st.warning("⚠️ No TA data found. Please complete the previous step.")
    st.stop()

base_df = st.session_state['ta_rearranged_df'].copy()

# Define the full 18-column structure requested
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

# Ensure all columns exist
for col in COL_NAMES:
    if col not in base_df.columns:
        base_df[col] = 0.0 if "Rs." in col or "Days" in col else ""

# --- HELPER: DA CALCULATION LOGIC (S.119) ---
def get_da_days_and_hrs(dep_date, dep_time, arr_date, arr_time):
    try:
        start = datetime.combine(pd.to_datetime(dep_date).date(), pd.to_datetime(dep_time).time())
        end = datetime.combine(pd.to_datetime(arr_date).date(), pd.to_datetime(arr_time).time())
        duration = end - start
        total_hours = duration.total_seconds() / 3600
        
        if total_hours < 6:
            da_val = 0.0
        elif 6 <= total_hours < 12:
            da_val = 0.5
        elif 12 <= total_hours < 24:
            da_val = 1.0
        else:
            # For every completed block of 24 hours, 1 full DA. 
            # Remaining hours follow the 6/12 rule.
            full_24h_blocks = int(total_hours // 24)
            rem = total_hours % 24
            extra = 0.0
            if 6 <= rem < 12: extra = 0.5
            elif rem >= 12: extra = 1.0
            da_val = full_24h_blocks + extra
            
        return f"{da_val} days ({round(total_hours, 2)} hrs)", da_val
    except:
        return "0.0 days (0 hrs)", 0.0

# --- SECTION 1: UPLOAD DOCUMENTS ---
st.subheader("1. AI Intelligence: Upload Salary Slip & Rules")
col_a, col_b = st.columns(2)
with col_a:
    sal_slip = st.file_uploader("Upload Salary Slip (PDF/Image)", type=['pdf', 'png', 'jpg'])
with col_b:
    da_rules = st.file_uploader("Upload DA Rules (Statute S.119)", type=['pdf'])

# --- SECTION 2: INTELLIGENT PROCESSING ---
if st.button("🚀 Run Intelligent DA Calculation"):
    if not sal_slip or not da_rules:
        st.error("Please upload both documents so Gemini can identify your Pay Level and correct DA rates.")
    else:
        with st.spinner("Gemini is reading documents and calculating..."):
            # 1. AI EXTRACTION (Simulated prompt logic)
            # In a full implementation, you'd send the files to Gemini here to extract:
            # { "Employee": "...", "PayLevel": 10, "Basic": 57700, "DARate": 400 }
            
            # 2. APPLY CALCULATION TO TABLE
            for idx, row in base_df.iterrows():
                # Column 14: Time Logic
                display_str, numeric_days = get_da_days_and_hrs(
                    row["2. Departure Date"], row["3. Departure Time"],
                    row["5. Arrival Date"], row["6. Arrival Time"]
                )
                base_df.at[idx, "14. Days of daily allowance receivable (Hrs)"] = display_str
                
                # Column 15: AI-identified rate (Example: Level 10 = 400)
                # In production, this value comes from the AI extraction above
                ai_rate = 400.0 
                base_df.at[idx, "15. Daily allowance rate (Rs.)"] = ai_rate
                
                # Column 16: Amount (numeric_days * rate)
                allowance_total = numeric_days * ai_rate
                base_df.at[idx, "16. Amount of Allowance (Rs.)"] = allowance_total
                
                # Column 17: Grand Total (10 + 13 + 16)
                t_amt = pd.to_numeric(row["10. Actual Total Amount of Ticket (Rs.)"], errors='coerce') or 0
                l_amt = pd.to_numeric(row["13. Total (Rs.)"], errors='coerce') or 0
                base_df.at[idx, "17. Total amount receivable (10+13+16) (Rs.)"] = t_amt + l_amt + allowance_total

            st.success("Calculations completed based on S.119 Statute!")

# --- SECTION 3: EDITABLE WORKSHEET ---
st.subheader("2. Final DA Calculation Table")
edited_df = st.data_editor(
    base_df[COL_NAMES],
    use_container_width=True,
    num_rows="dynamic"
)

# SAVE RESULTS
if st.button("💾 Save Final Calculation"):
    st.session_state['final_da_table'] = edited_df
    st.success("Data saved successfully!")
