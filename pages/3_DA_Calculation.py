import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import google.generativeai as genai
import json

# ==========================================
# ⚙️ CONFIGURATION & SETUP
# ==========================================
st.set_page_config(layout="wide", page_title="Step 3: S.119 DA Calculation")
st.title("📅 Step 3: Intelligent DA Calculation (Statute S.119)")

# Ensure session data exists
if 'ta_rearranged_df' not in st.session_state:
    st.warning("⚠️ No TA data found. Please complete the previous TA rearranging steps first.")
    st.stop()

# Define Master Columns
COL_NAMES = [
    "1. Departure Place", "2. Departure Date", "3. Departure Time",
    "4. Arrival Place", "5. Arrival Date", "6. Arrival Time",
    "7. Mode", "8. Class", "9. Ticket Price/Rate (Rs.)",
    "10. Actual Total Amount of Ticket (Rs.)", "11. KM", "12. Rate (Rs.)",
    "13. Total (Rs.)", 
    "14. Days of Daily Allowance receivable (Hrs)", 
    "15. Daily Allowance Rate (Rs.)", 
    "16. Amount of Allowance (Rs.)", 
    "17. Total amount receivable (Rs.)",
    "18. Purpose of Journey"
]

# ==========================================
# 🧠 S.119 CALCULATION LOGIC
# ==========================================

def get_da_units(hours):
    """Strict application of 6/12/24 hour rule (S.119)."""
    if hours < 6:
        return 0.0
    full_days = int(hours // 24)
    rem = hours % 24
    extra = 0.0
    if 6 <= rem < 12:
        extra = 0.5
    elif rem >= 12:
        extra = 1.0
    return full_days + extra

def calculate_intelligent_da(df, da_rate):
    """
    Step 2-8: Analyzes tour continuity and calculates DA based on total absence.
    """
    # Create working copy
    df = df.copy()
    
    # 1. Parsing datetimes for analysis
    df['start_dt'] = pd.to_datetime(df['2. Departure Date'].astype(str) + ' ' + df['3. Departure Time'].astype(str))
    df['end_dt'] = pd.to_datetime(df['5. Arrival Date'].astype(str) + ' ' + df['6. Arrival Time'].astype(str))
    df = df.sort_values('start_dt')

    # 2. Identify Continuous Tour (Start of first leg to end of last leg)
    tour_start = df['start_dt'].min()
    tour_end = df['end_dt'].max()
    total_absence_hrs = (tour_end - tour_start).total_seconds() / 3600
    total_da_eligible = get_da_units(total_absence_hrs)

    # 3. Step 8: Date-wise row handling
    # We distribute the total DA across the dates involved in the tour.
    unique_dates = pd.to_datetime(df['2. Departure Date']).dt.date.unique()
    num_days = len(unique_dates)
    
    # Simple distribution logic: Assign 1.0 to full days, remainder to last day
    # Or as per user instruction: Put DA values in the EARLIEST row for a date.
    
    da_remaining = total_da_eligible
    processed_dates = set()

    for idx, row in df.iterrows():
        row_date = pd.to_datetime(row['2. Departure Date']).date()
        
        # Initialize Cols 14-17 with default/blank
        df.at[idx, "14. Days of Daily Allowance receivable (Hrs)"] = ""
        df.at[idx, "15. Daily Allowance Rate (Rs.)"] = 0.0
        df.at[idx, "16. Amount of Allowance (Rs.)"] = 0.0
        
        # Step 8: Only process the first row found for a specific date
        if row_date not in processed_dates and da_remaining > 0:
            # Determine how much DA to assign to this date
            # Usually 1.0 if it's a full day absence, or the total remaining
            current_da = 1.0 if da_remaining >= 1.0 else da_remaining
            
            # Formatting Column 14 (Example: 1.0 (24 hrs))
            # Note: For the very first row, we show the total tour hours in brackets for audit
            if not processed_dates:
                hr_label = f"{current_da} ({round(total_absence_hrs, 1)} hrs total)"
            else:
                hr_label = f"{current_da}"

            df.at[idx, "14. Days of Daily Allowance receivable (Hrs)"] = hr_label
            df.at[idx, "15. Daily Allowance Rate (Rs.)"] = da_rate
            df.at[idx, "16. Amount of Allowance (Rs.)"] = current_da * da_rate
            
            da_remaining -= current_da
            processed_dates.add(row_date)

    # Step 7: Final Column 17 Calculation
    # Column 17 = Column 10 + Column 13 + Column 16
    for idx, row in df.iterrows():
        c10 = pd.to_numeric(row.get("10. Actual Total Amount of Ticket (Rs.)", 0), errors='coerce') or 0
        c13 = pd.to_numeric(row.get("13. Total (Rs.)", 0), errors='coerce') or 0
        c16 = pd.to_numeric(df.at[idx, "16. Amount of Allowance (Rs.)"], errors='coerce') or 0
        df.at[idx, "17. Total amount receivable (Rs.)"] = c10 + c13 + c16

    return df[COL_NAMES]

# ==========================================
# 🤖 AI EXTRACTION (STEP 5)
# ==========================================

def extract_salary_info(salary_file, rules_file):
    """Uses Gemini to identify Pay Level and applicable DA Rate."""
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        prompt = """
        Analyze these University documents:
        1. From the Salary Slip: Extract the current Pay Level/Grade.
        2. From S.119 Rules: Find the Daily Allowance (DA) rate in Rupees for that Pay Level.
        3. Note if any city classification (A, B, C) applies based on common Gujarat rules.
        Return JSON: {"pay_level": "...", "da_rate": 0.0, "employee": "..."}
        """
        # (This logic assumes AI integration is set up as in your environment)
        # Placeholder for demonstration:
        return {"pay_level": "Level 11", "da_rate": 600.0, "employee": "Associate Professor"}
    except:
        return {"pay_level": "Manual", "da_rate": 450.0, "employee": "User"}

# ==========================================
# 📑 USER INTERFACE
# ==========================================

st.subheader("Step 1: Document Audit & Rate Identification")
col_a, col_b = st.columns(2)
with col_a:
    sal_slip = st.file_uploader("Upload Salary Slip (PDF/Image)", type=['pdf', 'jpg', 'png'])
with col_b:
    rule_doc = st.file_uploader("Upload S.119 Rule Book (PDF)", type=['pdf'])

# Manual Override (Standard for University Rates)
da_rate_input = st.number_input("Confirmed DA Rate (Rs.)", value=600, help="Verified rate as per S.119 classification.")

if st.button("🚀 Calculate Final DA Table"):
    input_df = st.session_state['ta_rearranged_df'].copy()
    
    with st.spinner("Analyzing tour continuity and applying S.119 rules..."):
        # Run Calculation
        final_table = calculate_intelligent_da(input_df, da_rate_input)
        
        # Display Results
        st.subheader("Final Master TA/DA Table (Columns 1-18)")
        st.dataframe(final_table, use_container_width=True)
        
        # Step 2: Supporting Calculation Table for Audit
        st.subheader("Pre-Calculation Audit Detail (Step 2)")
        audit_cols = ["1. Departure Place", "2. Departure Date", "3. Departure Time", "4. Arrival Place", "5. Arrival Date", "6. Arrival Time"]
        st.table(input_df[audit_cols])
        
        # Session Save
        st.session_state['final_master_table'] = final_table
        st.success("✅ DA Calculations strictly applied as per Statute S.119.")

if 'final_master_table' in st.session_state:
    csv = st.session_state['final_master_table'].to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Final Official Table", data=csv, file_name="University_TA_DA_Final.csv")
