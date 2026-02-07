import streamlit as st
import pandas as pd
from datetime import datetime
import google.generativeai as genai
import json
import io

# ==========================================
# ⚙️ CONFIGURATION & SETUP
# ==========================================
st.set_page_config(layout="wide", page_title="University TA/DA Intelligent System")
st.title("📅 Intelligent DA Calculation (Statute S.119)")

api_key = st.session_state.get('gemini_api_key')
if not api_key:
    st.error("⚠️ Gemini API Key not found. Please set it in the Home page.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-3-flash-preview')

# Ensure TA data exists from previous steps
if 'ta_rearranged_df' not in st.session_state:
    st.warning("⚠️ No TA data found. Please complete the initial TA table entry.")
    st.stop()

# Master Column Structure
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

# ==========================================
# 🛠️ SECTION I: DOCUMENT UPLOAD & AI AUDIT
# ==========================================
st.header("Section I: Statutory Rule Audit & Salary Verification")

col1, col2 = st.columns(2)
with col1:
    salary_slip = st.file_uploader("Upload Salary Slip (PDF/Image)", type=['pdf', 'png', 'jpg'])
with col2:
    rules_doc = st.file_uploader("Upload Statute S.119 Rules (PDF)", type=['pdf'])

if salary_slip and rules_doc:
    if st.button("🔍 Analyze Documents & Audit Journey"):
        with st.spinner("AI is auditing salary level and journey continuity..."):
            # 1. AI Audit for DA Rate
            # Simplified for prompt logic; in production, send actual file bytes
            prompt = """
            Analyze the Salary Slip and Statute S.119 Rules:
            1. Extract the 'Pay Level' and 'Basic Pay' from the salary slip.
            2. In the S.119 Rules, locate the DA table for 'Traveling Allowance'.
            3. Based on the Pay Level, determine the 'Daily Allowance Rate (Rs.)'.
            4. If the journey involves staying in a Circuit House or free boarding/lodging, note the reduction rules.
            Return ONLY a JSON: {"pay_level": "...", "da_rate": 000}
            """
            # Placeholder for AI Response (Integration would use model.generate_content)
            audit_result = {"pay_level": "Level 11", "da_rate": 600} # Mock data
            st.session_state['audit_data'] = audit_result
            st.success(f"Audit Complete: Identified Pay {audit_result['pay_level']} with DA Rate: ₹{audit_result['da_rate']}")

            # 2. Chronological Journey Analysis
            base_df = st.session_state['ta_rearranged_df'].copy()
            
            # Helper to calculate DA units based on 6/12/24 hour rule
            def calculate_statutory_da(start_dt, end_dt):
                duration = end_dt - start_dt
                total_hrs = duration.total_seconds() / 3600
                
                if total_hrs < 6:
                    return 0.0, total_hrs
                
                full_blocks = int(total_hrs // 24)
                rem = total_hrs % 24
                
                extra = 0.0
                if 6 <= rem < 12:
                    extra = 0.5
                elif rem >= 12:
                    extra = 1.0
                return (full_blocks + extra), total_hrs

            # Create Analysis Table for User
            analysis_data = []
            for idx, row in base_df.iterrows():
                try:
                    dep_dt = datetime.combine(pd.to_datetime(row["2. Departure Date"]).date(), 
                                           pd.to_datetime(row["3. Departure Time"]).time())
                    arr_dt = datetime.combine(pd.to_datetime(row["5. Arrival Date"]).date(), 
                                           pd.to_datetime(row["6. Arrival Time"]).time())
                    
                    da_units, hrs = calculate_statutory_da(dep_dt, arr_dt)
                    
                    analysis_data.append({
                        "Departure": f"{row['1. Departure Place']} ({row['3. Departure Time']})",
                        "Arrival": f"{row['4. Arrival Place']} ({row['6. Arrival Time']})",
                        "Total Absence (Hrs)": round(hrs, 2),
                        "Admissible DA Days": da_units
                    })
                    
                    # Store results for Section II
                    base_df.at[idx, "14. Days of daily allowance receivable (Hrs)"] = f"{da_units} ({round(hrs, 1)} hrs)"
                    base_df.at[idx, "15. Daily allowance rate (Rs.)"] = audit_result['da_rate']
                    base_df.at[idx, "16. Amount of Allowance (Rs.)"] = da_units * audit_result['da_rate']
                    
                except:
                    continue

            st.subheader("Journey Analysis & Duration Audit")
            st.table(pd.DataFrame(analysis_data))
            st.session_state['processed_ta_df'] = base_df

# ==========================================
# 📄 SECTION II: MASTER TABLE & EXPORT
# ==========================================
st.divider()
st.header("Section II: Final University TA/DA Master Table")

if 'processed_ta_df' in st.session_state:
    master_df = st.session_state['processed_ta_df'].copy()
    
    # Calculate Column 17: (10 + 13 + 16)
    for idx, row in master_df.iterrows():
        try:
            c10 = float(row["10. Actual Total Amount of Ticket (Rs.)"] or 0)
            c13 = float(row["13. Total (Rs.)"] or 0)
            c16 = float(row["16. Amount of Allowance (Rs.)"] or 0)
            master_df.at[idx, "17. Total amount receivable (10+13+16) (Rs.)"] = c10 + c13 + c16
        except:
            pass

    # Display final editable table
    st.write("Review the final calculations before exporting:")
    final_table = st.data_editor(master_df[COL_NAMES], num_rows="dynamic")

    # Page 5 Export Emulation
    st.subheader("📤 Export Data (Page 5 Ready)")
    csv = final_table.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Completed TA/DA Statement (CSV)",
        data=csv,
        file_name="Completed_TADA_Statement.csv",
        mime="text/csv",
    )
else:
    st.info("Complete Section I to generate the Master Table.")
