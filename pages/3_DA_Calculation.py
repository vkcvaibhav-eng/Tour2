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
if 'raw_diary_df' not in st.session_state or st.session_state['raw_diary_df'].empty:
    st.warning("⚠️ No Tour Diary found. Please complete 'Step 1: Tour Diary' first.")
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
            
            model = genai.GenerativeModel('gemini-3-flash-preview')
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
st.subheader("Generate Calculation")

col1, col2 = st.columns([1, 4])
if col1.button("🤖 Calculate DA with AI"):
    with st.spinner("Applying Rules to Tour Diary..."):
        try:
            # Prepare Diary Data
            diary_json = st.session_state['raw_diary_df'].to_json(orient='records', date_format='iso')
            
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
            Calculate the Daily Allowance (DA) for the following Tour Diary.

            **INPUT DATA (Tour Diary):**
            {diary_json}

            **USER RATES (Derived from Salary Slip):**
            - Ordinary Rate (100%): ₹{da_rate_ordinary}
            - Special/Hotel Rate (100%): ₹{da_rate_hotel}

            **RULES TO APPLY:**
            1. **Absence Duration (Per Day):**
               - < 6 hours: 30%
               - 6 to 12 hours: 50%
               - > 12 hours: 100%
            2. **City Classification:**
               {rules_instruction}
               - If the 'Place of Halt' is a Special City/Corporation Area, use Special Rate. Else use Ordinary.

            **INSTRUCTIONS:**
            1. Analyze the tour row by row.
            2. Calculate hours absent for each date.
            3. Determine if the Halt Place warrants Special or Ordinary rate.
            4. Calculate the final amount.

            **REQUIRED JSON OUTPUT FORMAT:**
            [
              {{
                "Date": "DD-MM-YYYY",
                "Place": "Name of City/Place",
                "Rate_Type": "Ordinary" or "Special",
                "Applicable_Rate": {da_rate_ordinary} or {da_rate_hotel},
                "Hours_Claimed": "Number of hours",
                "Percentage": "30%" or "50%" or "100%",
                "DA_Amount": "Calculated Amount"
              }}
            ]
            """
            
            input_content.insert(0, prompt)

            # Call Gemini
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-3-flash-preview')
            response = model.generate_content(input_content)
            
            # Parse JSON
            cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned_text)
            
            # Create DataFrame
            df_da = pd.DataFrame(data)
            
            # Save to Session
            st.session_state['final_da_data'] = df_da
            st.success("✅ Calculation Complete!")
            
        except Exception as e:
            st.error(f"Error during calculation: {e}")

# --- 5. EDIT & REVIEW ---
if 'final_da_data' in st.session_state:
    st.subheader("Review & Edit DA Claims")
    
    # Allow editing
    edited_da_df = st.data_editor(
        st.session_state['final_da_data'],
        num_rows="dynamic",
        use_container_width=True,
        key="da_editor",
        column_config={
            "DA_Amount": st.column_config.NumberColumn("DA Amount (₹)", format="%.2f"),
            "Applicable_Rate": st.column_config.NumberColumn("Rate Base (₹)", format="%.2f"),
        }
    )
    
    # Update Session State
    st.session_state['final_da_data'] = edited_da_df
    
    # Summary Metrics
    total_da = pd.to_numeric(edited_da_df['DA_Amount'], errors='coerce').sum()
    st.metric(label="Total Daily Allowance Claim", value=f"₹ {total_da:,.2f}")

    st.markdown("---")
    st.write("👉 **Next Step:** Go to '4_Export' to generate your document.")
