import streamlit as st
import pandas as pd
from datetime import datetime
import google.generativeai as genai
import json
import io

# ==========================================
# ⚙️ CONFIGURATION & SETUP
# ==========================================
st.set_page_config(layout="wide", page_title="University TA/DA Calculation System")
st.title("📅 Step 3: DA Statutory Calculation (Statute S.119)")

api_key = st.session_state.get('gemini_api_key')
if not api_key:
    st.error("⚠️ Gemini API Key not found. Please set it in the Home page.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-3-flash-preview')

# --- DATA IMPORT FROM STEP 2 ---
if 'ta_rearranged_df' not in st.session_state:
    st.warning("⚠️ No TA data found from Step 2. Please complete TA Calculation first.")
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
# 🛠️ SECTION I: STATUTORY DA CALCULATION
# ==========================================
st.header("Section I: DA Calculation & Rule Audit")
st.info("The AI will now audit your tour (Cols 1-7) and Salary Slip to calculate DA as per Statute S.119.")

col1, col2 = st.columns(2)
with col1:
    salary_slip = st.file_uploader("Upload Salary Slip", type=['pdf', 'png', 'jpg'], key="da_sal")
with col2:
    rules_doc = st.file_uploader("Upload Statute S.119 Rules", type=['pdf'], key="da_rules")

if salary_slip and rules_doc:
    if st.button("🚀 Calculate DA & Audit Tour"):
        with st.spinner("AI is analyzing journey duration and pay level..."):
            
            # 1. AI PAY LEVEL AUDIT
            salary_blob = {"mime_type": salary_slip.type, "data": salary_slip.getvalue()}
            rules_blob = {"mime_type": rules_doc.type, "data": rules_doc.getvalue()}
            
            audit_prompt = """
            Identify the employee's 'Pay Level' and 'Basic Pay' from the salary slip.
            Locate the 'Daily Allowance Rate' table in the S.119 Rules.
            Match the Pay Level to the rate. Check for Circuit House/Boarding reductions.
            Return ONLY JSON: {"pay_level": "Level X", "da_rate": 000}
            """
            
            try:
                response = model.generate_content([audit_prompt, salary_blob, rules_blob])
                audit_result = json.loads(response.text.replace('```json', '').replace('```', '').strip())
                da_rate = audit_result['da_rate']
            except:
                st.error("Audit failed. Using manual rate.")
                da_rate = 0

            # 2. STATUTORY TIME CALCULATION (6/12/24 Hour Rules)
            base_df = st.session_state['ta_rearranged_df'].copy()
            
            def calculate_s119_da(start_dt, end_dt):
                duration = end_dt - start_dt
                total_hrs = duration.total_seconds() / 3600
                
                if total_hrs < 6:
                    return 0.0, total_hrs
                
                # Full 24-hour blocks
                full_days = int(total_hrs // 24)
                remainder = total_hrs % 24
                
                # Regulating the remaining period
                extra_day = 0.0
                if 6 <= remainder < 12:
                    extra_day = 0.5
                elif remainder >= 12:
                    extra_day = 1.0
                
                return (full_days + extra_day), total_hrs

            # Calculation Loop
            for idx, row in base_df.iterrows():
                try:
                    # Convert inputs to datetime objects
                    dep_dt = datetime.combine(pd.to_datetime(row["2. Departure Date"]).date(), 
                                           pd.to_datetime(row["3. Departure Time"]).time())
                    arr_dt = datetime.combine(pd.to_datetime(row["5. Arrival Date"]).date(), 
                                           pd.to_datetime(row["6. Arrival Time"]).time())
                    
                    da_days, total_hrs = calculate_s119_da(dep_dt, arr_dt)
                    
                    # Fill Column 14: Admissible Days (Total Hours)
                    base_df.at[idx, "14. Days of daily allowance receivable (Hrs)"] = f"{da_days} ({round(total_hrs, 1)} hrs)"
                    
                    # Fill Column 15: Rate
                    base_df.at[idx, "15. Daily allowance rate (Rs.)"] = da_rate
                    
                    # Fill Column 16: Calculation (Col 14 * Col 15)
                    base_df.at[idx, "16. Amount of Allowance (Rs.)"] = da_days * da_rate
                except:
                    continue

            st.success(f"DA Calculation Complete for {audit_result['pay_level']} at ₹{da_rate}/day.")
            st.session_state['processed_da_df'] = base_df

# ==========================================
# 📄 SECTION II: FINAL MASTER TABLE
# ==========================================
st.divider()
st.header("Section II: Final University TA/DA Master Table")

if 'processed_da_df' in st.session_state:
    master_df = st.session_state['processed_da_df'].copy()
    
    # Calculate Column 17: Sum of 10 + 13 + 16
    for idx, row in master_df.iterrows():
        try:
            c10 = float(pd.to_numeric(row["10. Actual Total Amount of Ticket (Rs.)"], errors='coerce') or 0)
            c13 = float(pd.to_numeric(row["13. Total (Rs.)"], errors='coerce') or 0)
            c16 = float(pd.to_numeric(row["16. Amount of Allowance (Rs.)"], errors='coerce') or 0)
            master_df.at[idx, "17. Total amount receivable (10+13+16) (Rs.)"] = c10 + c13 + c16
        except:
            master_df.at[idx, "17. Total amount receivable (10+13+16) (Rs.)"] = 0

    # Ensure all 18 columns exist and are ordered correctly
    for col in COL_NAMES:
        if col not in master_df.columns:
            master_df[col] = ""

    st.write("Full Master Table (Columns 1–18):")
    final_table = st.data_editor(master_df[COL_NAMES], use_container_width=True, key="final_editor")

    # Final CSV Export
    csv = final_table.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Completed TA/DA Bill (Page 5 Ready)",
        data=csv,
        file_name=f"University_TA_DA_Bill_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
else:
    st.info("Complete the document audit in Section I to see the results here.")
