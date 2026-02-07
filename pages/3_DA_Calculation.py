import streamlit as st
import pandas as pd
from datetime import datetime
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

# --- CRITICAL FIX: EXACT COLUMN NAMES MATCHING STEP 2 ---
COL_NAMES = [
    "1. Departure Place", "2. Departure Date", "3. Departure Time",
    "4. Arrival Place", "5. Arrival Date", "6. Arrival Time",
    "7. Mode", "8. Class", "9. Ticket Price/Rate (Rs.)",
    "10. Actual Total Amount of Ticket (Rs.)", 
    "11. KM", 
    "12. Rate (Rs.) (Auto/Taxi/Pvt)", # Fixed to match Step 2
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
    """Calculates DA based on total absence and tour continuity."""
    df = df.copy()
    
    # Pre-filling new columns to avoid IndexErrors
    for col in COL_NAMES:
        if col not in df.columns:
            df[col] = ""

    # Parse datetimes
    df['start_dt'] = pd.to_datetime(df['1. Departure Place'].astype(str).map(lambda x: '') + df['2. Departure Date'].astype(str) + ' ' + df['3. Departure Time'].astype(str), errors='coerce')
    df['end_dt'] = pd.to_datetime(df['4. Arrival Place'].astype(str).map(lambda x: '') + df['5. Arrival Date'].astype(str) + ' ' + df['6. Arrival Time'].astype(str), errors='coerce')
    
    df = df.sort_values('start_dt')

    # Identify Continuous Tour
    tour_start = df['start_dt'].min()
    tour_end = df['end_dt'].max()
    
    if pd.isnull(tour_start) or pd.isnull(tour_end):
        st.error("Error: Could not parse dates/times. Please check the format in Step 2.")
        return df[COL_NAMES]

    total_absence_hrs = (tour_end - tour_start).total_seconds() / 3600
    total_da_eligible = get_da_units(total_absence_hrs)

    # Date-wise row handling
    da_remaining = total_da_eligible
    processed_dates = set()

    for idx, row in df.iterrows():
        row_date = pd.to_datetime(row['2. Departure Date']).date()
        
        # Default blanks
        df.at[idx, "14. Days of Daily Allowance receivable (Hrs)"] = ""
        df.at[idx, "15. Daily Allowance Rate (Rs.)"] = 0.0
        df.at[idx, "16. Amount of Allowance (Rs.)"] = 0.0
        
        # Only first row of a specific date gets DA
        if row_date not in processed_dates and da_remaining > 0:
            current_da = 1.0 if da_remaining >= 1.0 else da_remaining
            
            if not processed_dates:
                hr_label = f"{current_da} ({round(total_absence_hrs, 1)} hrs total)"
            else:
                hr_label = f"{current_da}"

            df.at[idx, "14. Days of Daily Allowance receivable (Hrs)"] = hr_label
            df.at[idx, "15. Daily Allowance Rate (Rs.)"] = da_rate
            df.at[idx, "16. Amount of Allowance (Rs.)"] = current_da * da_rate
            
            da_remaining -= current_da
            processed_dates.add(row_date)

    # Final Column 17 Calculation
    for idx, row in df.iterrows():
        c10 = pd.to_numeric(row.get("10. Actual Total Amount of Ticket (Rs.)", 0), errors='coerce') or 0
        c13 = pd.to_numeric(row.get("13. Total (Rs.)", 0), errors='coerce') or 0
        c16 = pd.to_numeric(df.at[idx, "16. Amount of Allowance (Rs.)"], errors='coerce') or 0
        df.at[idx, "17. Total amount receivable (Rs.)"] = c10 + c13 + c16

    return df[COL_NAMES]

# ==========================================
# 📑 UI AND EXECUTION
# ==========================================

st.subheader("Step 1: Rate Identification")
da_rate_input = st.number_input("Confirmed DA Rate (Rs.)", value=600)

if st.button("🚀 Calculate Final DA Table"):
    input_df = st.session_state['ta_rearranged_df'].copy()
    
    # Ensure Column 18 exists from Step 2
    if "18. Purpose of Journey" not in input_df.columns:
        input_df["18. Purpose of Journey"] = ""

    with st.spinner("Applying S.119 rules..."):
        final_table = calculate_intelligent_da(input_df, da_rate_input)
        
        st.subheader("Final Master TA/DA Table (Columns 1-18)")
        st.dataframe(final_table, use_container_width=True)
        
        st.session_state['final_master_table'] = final_table
        st.success("✅ DA Calculations applied.")

if 'final_master_table' in st.session_state:
    csv = st.session_state['final_master_table'].to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Official Table", data=csv, file_name="TA_DA_Final.csv")
