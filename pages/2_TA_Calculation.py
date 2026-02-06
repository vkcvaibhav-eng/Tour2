import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import io
from datetime import datetime

# ==========================================
# ⚙️ CONFIGURATION & SETUP
# ==========================================
st.set_page_config(layout="wide", page_title="Step 2: TA Calculation & Validation")

api_key = st.session_state.get('gemini_api_key')
if not api_key:
    st.error("⚠️ Gemini API Key not found. Please set it in the Home page.")
    st.stop()

genai.configure(api_key=api_key)

# ==========================================
# 🧠 AI ENGINE: DOCUMENT VALIDATION
# ==========================================
def validate_against_rules(table_df, salary_info, rules_text):
    """Uses Gemini to compare the TA table against uploaded rules and salary slip."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    table_json = table_df.to_json(orient="records")
    
    prompt = f"""
    Compare the following TA Claim Table with the user's Salary Info and Company Regulations.
    
    Salary Info: {salary_info}
    Regulations/Rules: {rules_text}
    Claim Table: {table_json}
    
    TASKS:
    1. Check if the 'Class' (Col 8) is allowed for the user's Pay Level.
    2. Check if the 'Rate' (Col 12) matches the allowed rate for Auto/Taxi in the rules.
    3. Identify any disparity or rule violations.
    
    Return a clear summary. If everything is correct, start the message with 'VALIDATED'.
    """
    response = model.generate_content(prompt)
    return response.text

# ==========================================
# 🗓️ DATA PROCESSING & REARRANGING
# ==========================================
if 'final_tour_diary' not in st.session_state:
    st.error("⚠️ Please complete Step 1 (Tour Diary) first.")
    st.stop()

# Load the diary
df = st.session_state['final_tour_diary'].copy()

def smart_calculation_logic(row):
    mode = str(row.get("Mode_of_Travel", "")).lower()
    
    # 1. KM Logic: If missing, try to estimate or ask
    km = pd.to_numeric(row.get("KM", 0), errors='coerce')
    if pd.isna(km) or km == 0:
        # Fallback: We'll highlight this for manual entry in the editor
        km = 0.0

    # 2. Defaults for new columns
    travel_class = "Economic/General"
    ticket_rate = 0.0
    
    # Pre-fill Class based on Mode
    if "rail" in mode: travel_class = "2nd AC"
    elif "flight" in mode: travel_class = "Economy"
    elif "bus" in mode: travel_class = "Express"
    
    rate_per_km = 0.0
    # Set default rates if auto/taxi (User can override manually)
    if "auto" in mode or "rickshaw" in mode: rate_per_km = 15.0 
    
    actual_ticket = ticket_rate # Col 10
    total_amount = actual_ticket + (km * rate_per_km) # Col 13

    # Return in specific Column Order 1-13
    return pd.Series([
        row.get("Departure_Place"), # 1
        row.get("Departure_Date"),  # 2
        row.get("Departure_Time"),  # 3
        row.get("Arrival_Place"),    # 4
        row.get("Arrival_Date"),    # 5
        row.get("Arrival_Time"),    # 6
        row.get("Mode_of_Travel"),  # 7
        travel_class,               # 8 (Class)
        ticket_rate,                # 9 (Price)
        actual_ticket,              # 10 (Total Ticket)
        km,                         # 11 (KM)
        rate_per_km,                # 12 (Rate)
        total_amount                # 13 (Total)
    ])

# Initialize the stateful calculation table
if 'ta_rearranged_df' not in st.session_state:
    ta_df = df.apply(smart_calculation_logic, axis=1)
    ta_df.columns = [
        "1. Dep Place", "2. Dep Date", "3. Dep Time", 
        "4. Arr Place", "5. Arr Date", "6. Arr Time",
        "7. Mode", "8. Class", "9. Ticket Rate", 
        "10. Actual Ticket", "11. KM", "12. Rate/KM", "13. Total (Rs.)"
    ]
    st.session_state['ta_rearranged_df'] = ta_df

# ==========================================
# 📝 UI: THE REARRANGED TABLE
# ==========================================
st.title("🧮 TA Calculation (Columns 1-13)")
st.info("Please fill in missing KM (Col 11) or Rates (Col 12) manually. The table will update automatically.")

edited_ta = st.data_editor(
    st.session_state['ta_rearranged_df'],
    use_container_width=True,
    num_rows="dynamic",
    key="ta_main_editor",
    column_config={
        "8. Class": st.column_config.SelectboxColumn(
            "8. Class", 
            options=["1st AC", "2nd AC", "3rd AC", "Sleeper", "Business", "Economy", "Express", "Super Express", "Local"]
        ),
        "9. Ticket Rate": st.column_config.NumberColumn("9. Rate (Rs.)", format="₹ %.2f"),
        "11. KM": st.column_config.NumberColumn("11. KM", help="If missing, please enter distance"),
        "12. Rate/KM": st.column_config.NumberColumn("12. Rate (Auto/Pvt)", format="₹ %.2f"),
        "13. Total (Rs.)": st.column_config.NumberColumn("13. Total", format="₹ %.2f", disabled=True)
    }
)

# Live calculation for the table
edited_ta["10. Actual Ticket"] = edited_ta["9. Ticket Rate"]
edited_ta["13. Total (Rs.)"] = edited_ta["10. Actual Ticket"] + (edited_ta["11. KM"] * edited_ta["12. Rate/KM"])
st.session_state['ta_rearranged_df'] = edited_ta

# ==========================================
# 📑 RULES & SALARY SECTION
# ==========================================
st.divider()
st.subheader("📑 Rule Validation & Policy Check")

col_left, col_right = st.columns(2)

with col_left:
    st.write("**Upload TA Regulations/Rules**")
    rules_file = st.file_uploader("Upload PDF of TA Rules", type=['pdf', 'txt'])
    
with col_right:
    st.write("**Upload Salary Slip**")
    sal_file = st.file_uploader("Upload Salary Slip (for Pay Level)", type=['pdf', 'png', 'jpg'])

if st.button("⚖️ Validate Claims against Rules"):
    if not rules_file or not sal_file:
        st.warning("Please upload both Rules and Salary Slip for AI validation.")
    else:
        with st.spinner("AI checking for rule disparities..."):
            # Mocking extraction for this example (re-use your existing extraction logic here)
            sal_info = st.session_state.get('user_salary_info', "Level 11")
            rules_content = "Extracted rules content..." 
            
            validation_msg = validate_against_rules(edited_ta, sal_info, rules_content)
            
            if "VALIDATED" in validation_msg.upper():
                st.success(validation_msg)
                st.session_state['rules_validated'] = True
            else:
                st.error("🚨 DISPARITY FOUND:")
                st.write(validation_msg)
                st.session_state['rules_validated'] = False

# ==========================================
# ➡️ NAVIGATION
# ==========================================
st.divider()
if st.session_state.get('rules_validated'):
    if st.button("Proceed to DA Calculation ➡️"):
        st.switch_page("pages/3_DA_Calculation.py")
else:
    st.button("Proceed to DA Calculation ➡️", disabled=True, help="Validate rules first")
