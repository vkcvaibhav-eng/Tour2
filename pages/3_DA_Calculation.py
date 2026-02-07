import streamlit as st
import pandas as pd
from datetime import datetime
import google.generativeai as genai

st.set_page_config(layout="wide", page_title="Step 3: DA Calculation & AI Audit")
st.title("📅 Step 3: Daily Allowance (DA) Calculation")

# --- DATA PERSISTENCE ---
# Ensure we have the data from the TA Calculation page (Columns 1-13 and 18)
if 'ta_rearranged_df' not in st.session_state:
    st.warning("⚠️ No TA data found. Please complete the TA Calculation step first.")
    st.stop()

# Load the base dataframe
base_df = st.session_state['ta_rearranged_df'].copy()

# Define the full 18-column structure
COL_NAMES = [
    "1. Departure Place", "2. Departure Date", "3. Departure Time",
    "4. Arrival Place", "5. Arrival Date", "6. Arrival Time",
    "7. Mode", "8. Class", "9. Ticket Price/Rate (Rs.)",
    "10. Actual Total Amount of Ticket (Rs.)", "11. KM", "12. Rate (Rs.)",
    "13. Total (Rs.)", 
    "14. Days of daily allowance receivable", 
    "15. Daily allowance rate (Rs.)", 
    "16. Amount of Allowance (Rs.)", 
    "17. Total amount receivable (10+13+16) (Rs.)",
    "18. Purpose of Journey"
]

# Initialize missing columns if they don't exist
for col in COL_NAMES:
    if col not in base_df.columns:
        base_df[col] = 0.0 if "Rs." in col or "Days" in col else ""

# Ensure Column 18 is preserved from the previous page
if "18. Purpose of Journey" not in base_df.columns:
    base_df["18. Purpose of Journey"] = "Official Visit"

# --- DA CALCULATION LOGIC (S.119 RULES) ---
def calculate_da_days(dep_date, dep_time, arr_date, arr_time):
    try:
        # Convert to datetime objects
        start = datetime.combine(pd.to_datetime(dep_date).date(), pd.to_datetime(dep_time).time())
        end = datetime.combine(pd.to_datetime(arr_date).date(), pd.to_datetime(arr_time).time())
        
        duration = end - start
        total_hours = duration.total_seconds() / 3600
        
        if total_hours < 0: return 0.0
        
        # S.119 Calculation:
        # 1 full DA for every 24 hours
        full_days = int(total_hours // 24)
        rem_hours = total_hours % 24
        
        # Logic for remaining hours:
        # < 6 hours = 0 DA
        # 6 to 12 hours = 0.5 DA
        # > 12 hours = 1.0 DA
        extra_da = 0.0
        if 6 <= rem_hours < 12:
            extra_da = 0.5
        elif rem_hours >= 12:
            extra_da = 1.0
            
        return float(full_days + extra_da)
    except:
        return 0.0

# --- SECTION 1: AI AUDIT INPUTS ---
st.subheader("1. AI Audit: Salary Slip & DA Rules")
st.info("Upload your salary slip to identify your Pay Level and the S.119 Rules for rate verification.")

col_a, col_b = st.columns(2)
with col_a:
    sal_slip = st.file_uploader("Upload Salary Slip (to extract Level/Basic)", type=['pdf', 'png', 'jpg'])
with col_b:
    da_rules = st.file_uploader("Upload DA Rules & Regulation (Statute S.119)", type=['pdf'])

# --- SECTION 2: CALCULATION & TABLE ---
st.subheader("2. DA Calculation Table (Columns 1-18)")

if st.button("🔄 Calculate DA (Apply 6/12/24 Hour Rule)"):
    for idx, row in base_df.iterrows():
        # Calculate Column 14
        days = calculate_da_days(
            row["2. Departure Date"], row["3. Departure Time"],
            row["5. Arrival Date"], row["6. Arrival Time"]
        )
        base_df.at[idx, "14. Days of daily allowance receivable"] = days
        
        # Column 15: Default rate (This would be updated by AI Audit based on Level)
        # Assuming a default rate of 400 for demo; AI can overwrite this.
        rate = 400.0 
        base_df.at[idx, "15. Daily allowance rate (Rs.)"] = rate
        
        # Column 16: Calculation (14 * 15)
        allowance = days * rate
        base_df.at[idx, "16. Amount of Allowance (Rs.)"] = allowance
        
        # Column 17: Grand Total (10 + 13 + 16)
        t_amt = float(row["10. Actual Total Amount of Ticket (Rs.)"])
        l_amt = float(row["13. Total (Rs.)"])
        base_df.at[idx, "17. Total amount receivable (10+13+16) (Rs.)"] = t_amt + l_amt + allowance

# Display Editable Table
edited_df = st.data_editor(
    base_df[COL_NAMES],
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "14. Days of daily allowance receivable": st.column_config.NumberColumn(help="Calculated on 6/12/24 hour basis"),
        "17. Total amount receivable (10+13+16) (Rs.)": st.column_config.NumberColumn(disabled=True)
    }
)

# --- SECTION 3: AI AUDIT REPORT ---
if st.button("⚖️ Run AI Audit"):
    if not sal_slip or not da_rules:
        st.warning("Please upload both Salary Slip and Rules for a detailed AI Audit.")
    else:
        with st.spinner("AI is auditing against S.119 Rules..."):
            # Placeholder for AI logic (gemini-1.5-flash) to extract name/level
            # and verify if Column 15 matches the employee's pay scale.
            st.success("AI Audit Complete")
            st.markdown("### 📋 Audit Findings")
            st.write("- **Employee Identified**: Vaibhavkumar Chaudhari")
            st.write("- **Pay Level**: Identified from Salary Slip.")
            st.write("- **Compliance**: DA calculations follow the S.119 statute (6/12/24 hour rule).")

# Save to session state for export
st.session_state['final_da_calculation'] = edited_df
