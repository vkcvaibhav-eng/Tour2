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
st.title("📅 Step 3: AI-Driven DA Calculation (Statute S.119)")

api_key = st.session_state.get('gemini_api_key')
if not api_key:
    st.error("⚠️ Gemini API Key not found. Please set it in the Home page.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-3-flash-preview')

# --- DATA IMPORT FROM PREVIOUS STEP ---
if 'ta_rearranged_df' not in st.session_state:
    st.warning("⚠️ No TA data found. Please complete Step 2 (TA Calculation) first.")
    st.stop()

# Master Column Structure (18 Columns)
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
st.info("Upload documents to determine your Pay Level and applicable DA rates under Statute S.119.")

col1, col2 = st.columns(2)
with col1:
    salary_slip = st.file_uploader("Upload Salary Slip (PDF/Image)", type=['pdf', 'png', 'jpg'], key="da_sal")
with col2:
    rules_doc = st.file_uploader("Upload Statute S.119 Rules (PDF)", type=['pdf'], key="da_rules")

if salary_slip and rules_doc:
    if st.button("🔍 Run Statutory Audit & Journey Analysis"):
        with st.spinner("AI is auditing salary level and journey continuity..."):
            
            # 1. AI Audit for DA Rate
            salary_blob = {"mime_type": salary_slip.type, "data": salary_slip.getvalue()}
            rules_blob = {"mime_type": rules_doc.type, "data": rules_doc.getvalue()}
            
            audit_prompt = """
            Analyze the Salary Slip and Statute S.119 Rules:
            1. Extract 'Pay Level' and 'Basic Pay' from the salary slip.
            2. Find the DA Rate (Rs.) in S.119 Rules for this Pay Level.
            3. Check for reductions (Free boarding/lodging/Circuit House).
            Return ONLY valid JSON: {"pay_level": "Level X", "da_rate": 000}
            """
            
            try:
                response = model.generate_content([audit_prompt, salary_blob, rules_blob])
                audit_result = json.loads(response.text.replace('```json', '').replace('```', '').strip())
            except:
                st.error("AI could not parse documents. Using default manual entry.")
                audit_result = {"pay_level": "Manual", "da_rate": 0}

            st.success(f"Audit Complete: {audit_result['pay_level']} | Base DA Rate: ₹{audit_result['da_rate']}")

            # 2. Chronological Journey Analysis (S.119 Rule: 6/12/24 Hours)
            base_df = st.session_state['ta_rearranged_df'].copy()
            
            # Ensure Column 18 exists from Step 1/2
            if "18. Purpose of Journey" not in base_df.columns:
                base_df["18. Purpose of Journey"] = ""

            def calculate_statutory_da(start_dt, end_dt):
                duration = end_dt - start_dt
                total_hrs = duration.total_seconds() / 3600
                if total_hrs < 6: return 0.0, total_hrs
                
                full_blocks = int(total_hrs // 24)
                rem = total_hrs % 24
                extra = 0.5 if 6 <= rem < 12 else 1.0 if rem >= 12 else 0.0
                return (full_blocks + extra), total_hrs

            analysis_data = []
            for idx, row in base_df.iterrows():
                try:
                    dep_dt = datetime.combine(pd.to_datetime(row["2. Departure Date"]).date(), 
                                           pd.to_datetime(row["3. Departure Time"]).time())
                    arr_dt = datetime.combine(pd.to_datetime(row["5. Arrival Date"]).date(), 
                                           pd.to_datetime(row["6. Arrival Time"]).time())
                    
                    da_units, hrs = calculate_statutory_da(dep_dt, arr_dt)
                    
                    # Store values in temporary analysis and the master dataframe
                    base_df.at[idx, "14. Days of daily allowance receivable (Hrs)"] = f"{da_units} ({round(hrs, 1)} hrs)"
                    base_df.at[idx, "15. Daily allowance rate (Rs.)"] = audit_result['da_rate']
                    base_df.at[idx, "16. Amount of Allowance (Rs.)"] = da_units * audit_result['da_rate']
                    
                    analysis_data.append({
                        "Date": row["2. Departure Date"],
                        "Journey": f"{row['1. Departure Place']} ➔ {row['4. Arrival Place']}",
                        "Absence (Hrs)": round(hrs, 1),
                        "DA Admissible": da_units
                    })
                except Exception as e:
                    continue

            st.subheader("Journey Continuity Audit (S.119 Logic)")
            st.table(pd.DataFrame(analysis_data))
            st.session_state['processed_ta_df'] = base_df

# ==========================================
# 📄 SECTION II: MASTER TABLE & EXPORT
# ==========================================
st.divider()
st.header("Section II: Final University TA/DA Master Table")

if 'processed_ta_df' in st.session_state:
    master_df = st.session_state['processed_ta_df'].copy()
    
    # Calculate Column 17: Total Receivable (Ticket + KM Total + DA)
    for idx, row in master_df.iterrows():
        try:
            c10 = float(pd.to_numeric(row["10. Actual Total Amount of Ticket (Rs.)"], errors='coerce') or 0)
            c13 = float(pd.to_numeric(row["13. Total (Rs.)"], errors='coerce') or 0)
            c16 = float(pd.to_numeric(row["16. Amount of Allowance (Rs.)"], errors='coerce') or 0)
            master_df.at[idx, "17. Total amount receivable (10+13+16) (Rs.)"] = c10 + c13 + c16
        except:
            master_df.at[idx, "17. Total amount receivable (10+13+16) (Rs.)"] = 0

    # Ensure all columns exist for the final structure
    for col in COL_NAMES:
        if col not in master_df.columns:
            master_df[col] = ""

    st.write("Review final Columns 1–18. Column 14–17 have been AI-calculated.")
    final_table = st.data_editor(master_df[COL_NAMES], use_container_width=True, num_rows="dynamic")

    # Final Export
    st.subheader("📤 Step 5: Export for Submission")
    csv = final_table.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Completed TA/DA Bill (CSV)",
        data=csv,
        file_name=f"TA_Bill_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
else:
    st.info("Please complete the Audit in Section I to generate the Master Table.")
