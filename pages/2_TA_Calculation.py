import streamlit as st
import pandas as pd
from datetime import datetime
import google.generativeai as genai
import json

# ==========================================
# ⚙️ CONFIGURATION & SETUP
# ==========================================
st.set_page_config(layout="wide", page_title="University TA/DA Calculation System")
st.title("📅 Step 3: Statutory DA Calculation (Statute S.119)")

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
# 🛠️ SECTION I: CALCULATE DA (Rate & Time)
# ==========================================
st.header("Section I: DA Rate Determination & Calculation")
st.info("Upload your Salary Slip and Rules. The AI will determine your Rate, and the system will calculate DA days based on Statute S.119.")

col1, col2 = st.columns(2)
with col1:
    salary_slip = st.file_uploader("Upload Salary Slip", type=['pdf', 'png', 'jpg'], key="da_sal")
with col2:
    rules_doc = st.file_uploader("Upload Statute S.119 Rules", type=['pdf'], key="da_rules")

if salary_slip and rules_doc:
    if st.button("🚀 Calculate Daily Allowance"):
        with st.spinner("Determining Pay Level and Calculating Admissible Days..."):
            
            # 1. GET DA RATE VIA AI (From Documents)
            salary_blob = {"mime_type": salary_slip.type, "data": salary_slip.getvalue()}
            rules_blob = {"mime_type": rules_doc.type, "data": rules_doc.getvalue()}
            
            rate_prompt = """
            Review the Salary Slip to find the 'Pay Level'. 
            Review the Statute S.119 Rules to find the 'Daily Allowance Rate' for that level.
            Check for any reductions (Circuit House, etc.).
            Return ONLY a JSON object: {"da_rate": 000}
            """
            
            try:
                response = model.generate_content([rate_prompt, salary_blob, rules_blob])
                # Clean and parse JSON
                clean_text = response.text.replace('```json', '').replace('```', '').strip()
                da_rate = json.loads(clean_text).get('da_rate', 0)
            except:
                st.error("Could not automatically determine rate. Defaulting to 0.")
                da_rate = 0

            # 2. PERFORM STATUTORY CALCULATION (Python Logic)
            base_df = st.session_state['ta_rearranged_df'].copy()
            
            # Ensure columns exist before processing
            for col in ["14. Days of daily allowance receivable (Hrs)", "15. Daily allowance rate (Rs.)", "16. Amount of Allowance (Rs.)"]:
                if col not in base_df.columns:
                    base_df[col] = ""

            # Function: S.119 6/12/24 Hour Rule
            def calculate_da_statute_s119(start_dt, end_dt):
                duration = end_dt - start_dt
                total_hrs = duration.total_seconds() / 3600
                
                # Rule: No DA for < 6 hours
                if total_hrs < 6:
                    return 0.0, total_hrs
                
                # Rule: Full blocks of 24 hours
                full_days = int(total_hrs // 24)
                remainder = total_hrs % 24
                
                # Rule: Regulate the remaining period
                extra_day = 0.0
                if 6 <= remainder < 12:
                    extra_day = 0.5  # Half DA
                elif remainder >= 12:
                    extra_day = 1.0  # Full DA
                
                return (full_days + extra_day), total_hrs

            # Apply calculation row-by-row
            for idx, row in base_df.iterrows():
                try:
                    # Parse Dates
                    d_date = pd.to_datetime(row["2. Departure Date"], dayfirst=True).date()
                    d_time = pd.to_datetime(row["3. Departure Time"]).time()
                    a_date = pd.to_datetime(row["5. Arrival Date"], dayfirst=True).date()
                    a_time = pd.to_datetime(row["6. Arrival Time"]).time()
                    
                    dep_dt = datetime.combine(d_date, d_time)
                    arr_dt = datetime.combine(a_date, a_time)
                    
                    # Calculate
                    da_days, hrs = calculate_da_statute_s119(dep_dt, arr_dt)
                    
                    # Fill Dataframe
                    base_df.at[idx, "14. Days of daily allowance receivable (Hrs)"] = f"{da_days} ({round(hrs, 1)} hrs)"
                    base_df.at[idx, "15. Daily allowance rate (Rs.)"] = da_rate
                    base_df.at[idx, "16. Amount of Allowance (Rs.)"] = da_days * da_rate
                    
                except Exception as e:
                    # Handle empty rows or parsing errors gracefully
                    continue

            # 3. DISPLAY TABLE EXACTLY LIKE THE IMAGE
            st.success(f"Calculation Complete. Applicable Rate: ₹{da_rate}")
            st.subheader("Date-wise DA Breakdown")
            
            # Create a specific view matching the image columns
            # Using .get to avoid KeyErrors if columns are missing for some reason, though they are initialized above
            da_display_df = base_df[[
                "2. Departure Date", 
                "14. Days of daily allowance receivable (Hrs)", 
                "15. Daily allowance rate (Rs.)", 
                "16. Amount of Allowance (Rs.)"
            ]].copy()
            
            # Rename columns to match the image exactly
            da_display_df.columns = [
                "Date", 
                "Days of daily allowance receivable", 
                "Daily allowance rate (Rs.)", 
                "Amount of Allowance (Rs.)"
            ]
            
            # Use st.table for the exact look requested
            st.table(da_display_df)
            
            # Save to session for Section II
            st.session_state['processed_da_df'] = base_df

# ==========================================
# 📄 SECTION II: MASTER TABLE & EXPORT
# ==========================================
st.divider()
st.header("Section II: Final University TA/DA Master Table")

if 'processed_da_df' in st.session_state:
    master_df = st.session_state['processed_da_df'].copy()
    
    # Calculate Column 17: Sum (Col 10 + Col 13 + Col 16)
    for idx, row in master_df.iterrows():
        try:
            c10 = float(pd.to_numeric(row.get("10. Actual Total Amount of Ticket (Rs.)", 0), errors='coerce') or 0)
            c13 = float(pd.to_numeric(row.get("13. Total (Rs.)", 0), errors='coerce') or 0)
            c16 = float(pd.to_numeric(row.get("16. Amount of Allowance (Rs.)", 0), errors='coerce') or 0)
            
            master_df.at[idx, "17. Total amount receivable (10+13+16) (Rs.)"] = c10 + c13 + c16
        except:
            master_df.at[idx, "17. Total amount receivable (10+13+16) (Rs.)"] = 0

    # Ensure Column 18 exists
    if "18. Purpose of Journey" not in master_df.columns:
        master_df["18. Purpose of Journey"] = ""

    # Display Editable Master Table
    st.write("Review the complete table below (Columns 1–18):")
    final_table = st.data_editor(
        master_df[COL_NAMES], 
        use_container_width=True, 
        height=500,
        num_rows="dynamic"
    )

    # PAGE 5 EXPORT
    st.subheader("📤 Export Data (Page 5)")
    csv = final_table.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Final TA/DA Statement (CSV)",
        data=csv,
        file_name="University_TADA_Final_Page5.csv",
        mime="text/csv",
    )
else:
    st.info("Please perform the calculation in Section I first.")

