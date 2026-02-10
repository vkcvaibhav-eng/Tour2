import streamlit as st
import pandas as pd
import json
import google.generativeai as genai
import tempfile
import os
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Step 3: DA Calculation")
st.title("💰 Step 3: Daily Allowance (DA) Calculation")
st.markdown("### Based on Statute S.119 & Uploaded Salary Slip")

# --- 1. SETUP & VALIDATION ---
# Check if Step 2 (TA Calculation) is done
if 'final_ta_data' not in st.session_state or st.session_state['final_ta_data'].empty:
    st.warning("⚠️ No TA Calculation data found. Please complete 'Step 2: TA Calculation' first.")
    st.info("This step requires the table with Columns 1-13 generated in the previous step.")
    st.stop()

api_key = st.session_state.get('gemini_api_key')
if not api_key:
    st.error("⚠️ Gemini API Key missing. Please set it in 'Home'.")
    st.stop()

# --- HELPER: FILE UPLOAD TO GEMINI ---
def upload_to_gemini(uploaded_file, mime_type=None):
    """Saves uploaded file to temp and uploads to Gemini."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        genai.configure(api_key=api_key)
        gemini_file = genai.upload_file(tmp_path, mime_type=mime_type or uploaded_file.type)
        return gemini_file
    except Exception as e:
        st.error(f"Error uploading file to AI: {e}")
        return None

# --- 2. SIDEBAR: EVIDENCE UPLOADS ---
st.sidebar.header("1. Upload Evidence")
st.sidebar.info("Upload documents to auto-calculate rates.")

salary_slip = st.sidebar.file_uploader("Upload Salary Slip", type=['pdf', 'jpg', 'jpeg', 'png'])
da_rules_pdf = st.sidebar.file_uploader("Upload DA Rules (PDF)", type=['pdf'])

# --- 3. AUTO-DETECT RATES FROM SLIP ---
st.sidebar.header("2. Configure Rates")

# Initialize session state for rates if not present
if 'detected_ord_rate' not in st.session_state:
    st.session_state['detected_ord_rate'] = 500
if 'detected_hotel_rate' not in st.session_state:
    st.session_state['detected_hotel_rate'] = 1000

# Button to analyze salary slip
if salary_slip and st.sidebar.button("🪄 Auto-detect Rates from Slip"):
    with st.spinner("Analyzing Salary Slip & Rules..."):
        try:
            # Upload files to Gemini
            gemini_slip = upload_to_gemini(salary_slip)
            files_to_send = [gemini_slip]
            
            rule_context = "Use general knowledge of Gujarat Agricultural University DA rates."
            if da_rules_pdf:
                gemini_rules = upload_to_gemini(da_rules_pdf)
                files_to_send.append(gemini_rules)
                rule_context = "Use the attached DA Rules PDF to find the rate matching the Grade Pay/Pay Level found in the Salary Slip."

            # Prompt to find rates
            rate_prompt = f"""
            Analyze the attached Salary Slip. 
            1. Identify the Employee's Grade Pay, Pay Level, or Basic Pay.
            2. {rule_context}
            3. Determine the eligible "Ordinary DA Rate" and "Hotel/Special DA Rate".
            
            Return ONLY a JSON object:
            {{
                "ordinary_rate": <number>,
                "special_rate": <number>,
                "reason": "<short explanation of pay level found>"
            }}
            """
            
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content([rate_prompt, *files_to_send])
            
            # Parse response
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            rates_data = json.loads(clean_json)
            
            # Update Session State
            st.session_state['detected_ord_rate'] = int(rates_data.get('ordinary_rate', 0))
            st.session_state['detected_hotel_rate'] = int(rates_data.get('special_rate', 0))
            st.sidebar.success(f"✅ Detected: {rates_data.get('reason')}")
            
        except Exception as e:
            st.sidebar.error(f"Could not auto-detect: {e}")

# Manual/Auto Inputs
da_rate_ordinary = st.sidebar.number_input(
    "Ordinary DA Rate (₹)", 
    min_value=0, 
    value=st.session_state['detected_ord_rate']
)

da_rate_hotel = st.sidebar.number_input(
    "Hotel/Special DA Rate (₹)", 
    min_value=0, 
    value=st.session_state['detected_hotel_rate']
)

# --- 4. CALCULATION ENGINE ---
st.subheader("Generate Final Calculation Table (Cols 1-16)")

col1, col2 = st.columns([1, 4])
if col1.button("🤖 Calculate Columns 14, 15, 16"):
    with st.spinner("Merging TA Data with DA Rules..."):
        try:
            # Prepare Step 2 Data (TA Table)
            # We assume the dataframe from Step 2 has columns 1 to 13.
            ta_df = st.session_state['final_ta_data']
            ta_json = ta_df.to_json(orient='records', date_format='iso')
            
            # Prepare Context Files (Rules)
            input_content = []
            
            if da_rules_pdf:
                gemini_rules_main = upload_to_gemini(da_rules_pdf)
                input_content.append(gemini_rules_main)
                rules_instruction = "Refer strictly to the attached DA Rules PDF for City Classifications (Tier-1/Corporation areas)."
            else:
                rules_instruction = """
                Use standard Gujarat Agricultural University rules:
                - Tier 1 Cities (Special Rate): Ahmedabad, Surat, Vadodara, Rajkot, Mumbai, Delhi, Bangalore, etc.
                - Others: Ordinary Rate.
                """

            # Construct Prompt
            prompt = f"""
            You are an accountant for an Agricultural University in Gujarat. 
            I have a Tour Diary table with Columns 1 to 13 filled (Ticket/Journey details).
            
            **YOUR TASK:**
            Reconstruct the table and **add Columns 14, 15, and 16** based on Statute S.119 DA Rules.

            **INPUT DATA (Columns 1-13):**
            {ta_json}

            **DA RATES:**
            - Ordinary Rate: ₹{da_rate_ordinary}
            - Special/Hotel Rate: ₹{da_rate_hotel}

            **LOGIC FOR NEW COLUMNS:**
            
            1. **Analyze Duration**: Look at "Departure Date/Time" and "Arrival Date/Time" for each row to understand the time spent.
               - Note: Usually DA is claimed for the *Halt* at the destination or the *Day* of travel.
               
            2. **Column 14: Days of daily allowance receivable**
               - Calculate hours absent/spent for that specific line item.
               - < 6 Hours: Write "0.3"
               - 6 to 12 Hours: Write "0.5"
               - > 12 Hours: Write "1.0"
               - If it is a return journey returning to HQ on the same day, sum the hours.
            
            3. **Column 15: Daily allowance rate (Rs.)**
               - Look at the "Arrival Place" (Col 4) or "Departure Place" (Col 1) depending on where the time was spent.
               - Use {da_rate_hotel} if it is a Major City (Ahmedabad, Surat, Bangalore, etc.) or Rules PDF.
               - Use {da_rate_ordinary} for other places.
               
            4. **Column 16: Amount of Allowance (Rs.)**
               - Calculate: (Value of Col 14) * (Value of Col 15).
               - Example: 0.5 * 1000 = 500.

            **OUTPUT FORMAT:**
            Return a JSON array where EVERY object has the original columns PLUS:
            - "14. Days of daily allowance receivable" (Number: 0.3, 0.5, or 1.0)
            - "15. Daily allowance rate (Rs.)" (Number)
            - "16. Amount of Allowance (Rs.)" (Number)
            """
            
            input_content.insert(0, prompt)

            # Call Gemini
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(input_content)
            
            # Parse JSON
            cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned_text)
            
            # Create DataFrame
            df_final = pd.DataFrame(data)
            
            # Save to Session
            st.session_state['final_da_data'] = df_final
            st.success("✅ Merged TA + DA Calculation Complete!")
            
        except Exception as e:
            st.error(f"Error during calculation: {e}")

# --- 5. EDIT & REVIEW ---
if 'final_da_data' in st.session_state:
    st.subheader("Review Final Combined Table (Cols 1-16)")
    st.markdown("This table merges your Journey Details (TA) with your Daily Allowance (DA).")
    
    # Allow editing
    edited_da_df = st.data_editor(
        st.session_state['final_da_data'],
        num_rows="dynamic",
        use_container_width=True,
        key="final_da_editor",
        column_config={
            "14. Days of daily allowance receivable": st.column_config.NumberColumn("14. DA Days (0.3/0.5/1)", format="%.1f"),
            "15. Daily allowance rate (Rs.)": st.column_config.NumberColumn("15. Rate (Rs.)", format="%.2f"),
            "16. Amount of Allowance (Rs.)": st.column_config.NumberColumn("16. DA Amount (Rs.)", format="%.2f"),
        }
    )
    
    # Update Session State
    st.session_state['final_da_data'] = edited_da_df
    
    # Calculate Grand Totals
    # We sum Col 13 (TA Total) and Col 16 (DA Total)
    
    total_ta_claim = 0
    total_da_claim = 0
    
    if "13. Total (Rs.)" in edited_da_df.columns:
        total_ta_claim = pd.to_numeric(edited_da_df["13. Total (Rs.)"], errors='coerce').sum()
        
    if "16. Amount of Allowance (Rs.)" in edited_da_df.columns:
        total_da_claim = pd.to_numeric(edited_da_df["16. Amount of Allowance (Rs.)"], errors='coerce').sum()

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total Transport (Col 13)", f"₹ {total_ta_claim:,.2f}")
    col_b.metric("Total DA (Col 16)", f"₹ {total_da_claim:,.2f}")
    col_c.metric("GRAND TOTAL CLAIM", f"₹ {total_ta_claim + total_da_claim:,.2f}")

    st.markdown("---")
    st.write("👉 **Next Step:** Go to '4_Export' to generate your final document.")
