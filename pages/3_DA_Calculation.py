import streamlit as st
import pandas as pd
from datetime import datetime
import google.generativeai as genai
import json

# ==========================================
# ⚙️ CONFIGURATION & DATA FORMATTING
# ==========================================
st.set_page_config(layout="wide", page_title="Intelligent DA Merger")
st.title("📅 Step 3: DA Calculation with Auto-Row Merging")

# --- EXPECTED DATA FORMAT HELP ---
with st.expander("ℹ️ Data Format Requirements (To avoid errors)"):
    st.write("""
    - **Date Format:** YYYY-MM-DD (e.g., 2026-02-17)
    - **Time Format:** HH:MM:SS (24-hour format, e.g., 14:30:00)
    - **Logic:** If multiple rows have the same Date, they will be merged for DA calculation.
    """)

if 'ta_rearranged_df' not in st.session_state:
    st.warning("⚠️ No data found from Step 2.")
    st.stop()

df = st.session_state['ta_rearranged_df'].copy()

# ==========================================
# 🧠 MERGING & CALCULATION LOGIC
# ==========================================

def calculate_da_statute(total_hours):
    """Applying S.119 Statute logic (6/12/24 Hour Rule)"""
    if total_hours < 6: return 0.0
    full_days = int(total_hours // 24)
    rem = total_hours % 24
    extra = 0.5 if 6 <= rem < 12 else (1.0 if rem >= 12 else 0.0)
    return full_days + extra

def merge_and_calculate_da(dataframe, ai_rate):
    # Ensure dates are datetime objects for sorting
    dataframe['2. Departure Date'] = pd.to_datetime(dataframe['2. Departure Date'])
    dataframe['5. Arrival Date'] = pd.to_datetime(dataframe['5. Arrival Date'])
    
    # Sort by date and time
    dataframe = dataframe.sort_values(by=['2. Departure Date', '3. Departure Time'])
    
    # We will group by the "Departure Date" to find same-day tours
    processed_rows = []
    
    # Grouping by date to merge rows
    for date, group in dataframe.groupby('2. Departure Date'):
        # Find earliest departure and latest arrival of the day
        start_time_str = group['3. Departure Time'].min()
        end_time_str = group['6. Arrival Time'].max()
        
        try:
            start_dt = datetime.combine(date, pd.to_datetime(start_time_str).time())
            # Use the arrival date of the last entry in the group
            end_date = group['5. Arrival Date'].max()
            end_dt = datetime.combine(end_date, pd.to_datetime(end_time_str).time())
            
            duration = end_dt - start_dt
            total_hrs = duration.total_seconds() / 3600
            da_days = calculate_da_statute(total_hrs)
            
            # Update all rows in this group with the same DA info (Merging effect)
            for idx in group.index:
                dataframe.at[idx, "14. Days of daily allowance receivable (Hrs)"] = f"{da_days} ({round(total_hrs, 1)} hrs)"
                dataframe.at[idx, "15. Daily allowance rate (Rs.)"] = ai_rate
                # Only put the amount in the FIRST row of the merged group to avoid double-counting
                if idx == group.index[0]:
                    dataframe.at[idx, "16. Amount of Allowance (Rs.)"] = da_days * ai_rate
                else:
                    dataframe.at[idx, "16. Amount of Allowance (Rs.)"] = 0.0
                    
                # Calculate Grand Total
                col10 = pd.to_numeric(dataframe.at[idx, "10. Actual Total Amount of Ticket (Rs.)"], errors='coerce') or 0
                col13 = pd.to_numeric(dataframe.at[idx, "13. Total (Rs.)"], errors='coerce') or 0
                dataframe.at[idx, "17. Total amount receivable (10+13+16) (Rs.)"] = col10 + col13 + dataframe.at[idx, "16. Amount of Allowance (Rs.)"]
        except Exception as e:
            st.error(f"Error calculating date {date}: {e}")
            
    return dataframe

# ==========================================
# 📑 UI & BUTTONS
# ==========================================

st.subheader("1. AI Audit Inputs")
c1, c2 = st.columns(2)
with c1: sal_up = st.file_uploader("Upload Salary Slip", type=['pdf','png','jpg'])
with c2: rule_up = st.file_uploader("Upload S.119 Rules", type=['pdf'])

if st.button("🚀 Merge Tours & Calculate DA"):
    if not sal_up or not rule_up:
        st.error("Please upload files first.")
    else:
        # Here Gemini would normally extract the rate. We'll use 400 for this example.
        processed_df = merge_and_calculate_da(df, 400.0)
        st.session_state['merged_da_df'] = processed_df
        st.success("Tours on the same day have been merged and calculated!")

if 'merged_da_df' in st.session_state:
    st.subheader("2. Final Result (Merged Columns 14, 15, 16)")
    st.data_editor(st.session_state['merged_da_df'], use_container_width=True)
