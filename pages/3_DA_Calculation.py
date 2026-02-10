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
    # For testing purposes, uncomment the line below to create dummy data if needed
    # st.session_state['raw_diary_df'] = pd.DataFrame([{"Date": "2023-10-01", "Place": "Ahmedabad", "Hours": 14}, {"Date": "2023-10-02", "Place": "Navsari", "Hours": 5}])
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
            
            model = genai.GenerativeModel('gemini-1.5-flash') # Updated to stable model
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
    "Hotel/Special DA Rate (₹) [Tier-1 Cities]", 
    min_value=0, 
    value=st.session_state['detected_hotel_rate']
)

# --- 4. CALCULATION ENGINE WITH AUDIT ---
st.subheader("Generate Calculation")

col1, col2 = st.columns([1, 4])
if col1.button("🤖 Calculate DA with AI Audit"):
    
    # 1. PREPARE DATA
    diary_json = st.session_state['raw_diary_df'].to_json(orient='records', date_format='iso')
    
    # Prepare Context Files (Rules)
    files_for_calc = []
    
    if da_rules_pdf:
        gemini_rules_main = upload_to_gemini(da_rules_pdf)
        files_for_calc.append(gemini_rules_main)
        rules_instruction = "Refer strictly to the attached DA Rules PDF for City Classifications (Tier-1/Corporation areas)."
    else:
        # Fallback hardcoded rules for Gujarat/Agri Universities
        rules_instruction = """
        Use standard Gujarat Govt / Agricultural University rules for City Tiers:
        - **Tier 1 (Special Rate):** Ahmedabad, Surat, Vadodara, Rajkot, Bhavnagar, Jamnagar, Gandhinagar, Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad.
        - **Tier 2 (Ordinary Rate):** All other villages, talukas, and smaller towns.
        """

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    # ----------------------------------------
    # PHASE 1: INITIAL CALCULATION
    # ----------------------------------------
    with st.status("🤖 Phase 1: Identifying Locations & Rates...", expanded=True) as status:
        try:
            prompt_phase_1 = f"""
            You are an Accountant. Calculate DA for the following Tour Diary.

            **INPUT DATA:**
            {diary_json}

            **RATES:**
            - Ordinary Rate: ₹{da_rate_ordinary}
            - Special (Tier-1) Rate: ₹{da_rate_hotel}

            **LOGIC:**
            1. **Identify Location Tier:** Check the 'Place' column. If it is a Tier-1 city (Corporation area/Metro), use Special Rate. Otherwise, use Ordinary Rate. {rules_instruction}
            2. **Calculate %:** <6 hrs = 30%, 6-12 hrs = 50%, >12 hrs = 100%.
            3. **Calculate Amount:** Rate * %.

            Return ONLY a valid JSON List.
            """
            
            response_1 = model.generate_content([prompt_phase_1, *files_for_calc])
            clean_json_1 = response_1.text.replace("```json", "").replace("```", "").strip()
            draft_data = json.loads(clean_json_1)
            
            status.write("✅ Phase 1 Complete. Initiating Audit...")

            # ----------------------------------------
            # PHASE 2: AI AUDIT (SELF-CORRECTION)
            # ----------------------------------------
            status.update(label="🕵️ Phase 2: Auditing for Errors...", state="running")
            
            prompt_audit = f"""
            You are a Senior Auditor. Review this Draft DA Claim for errors.

            **DRAFT CLAIM:**
            {json.dumps(draft_data)}

            **AUDIT RULES:**
            1. **Location Check:** Did the previous AI miss any Tier-1 cities? (e.g., if Place is 'Ahmedabad' but Rate used was {da_rate_ordinary}, CHANGE it to {da_rate_hotel}).
            2. **Math Check:** Ensure Rate * Percentage = Amount is mathematically perfect.
            3. **Logic Check:** Ensure <6 hours is strictly 30% (0.3).

            **INSTRUCTIONS:**
            - If you find errors, FIX THEM in the JSON.
            - If correct, return the JSON as is.
            - Return ONLY the final corrected JSON List.
            
            **REQUIRED OUTPUT FORMAT:**
            [
              {{
                "Date": "DD-MM-YYYY",
                "Place": "Name",
                "Rate_Type": "Ordinary" or "Special",
                "Applicable_Rate": <number>,
                "Hours_Claimed": <number/string>,
                "Percentage": "30%" or "50%" or "100%",
                "DA_Amount": <calculated_amount>,
                "Audit_Note": "Verified" or "Fixed rate for Tier-1 city"
              }}
            ]
            """
            
            response_audit = model.generate_content([prompt_audit]) # No files needed for audit, just logic
            clean_json_audit = response_audit.text.replace("```json", "").replace("```", "").strip()
            final_data = json.loads(clean_json_audit)
            
            # Save to Session
            df_da = pd.DataFrame(final_data)
            st.session_state['final_da_data'] = df_da
            
            status.update(label="✅ Audit Complete!", state="complete", expanded=False)
            st.success("Calculation verified and corrected by AI Auditor.")

        except Exception as e:
            st.error(f"Error during calculation/audit: {e}")
            st.stop()

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
            "Audit_Note": st.column_config.TextColumn("AI Audit Note", disabled=True),
        }
    )
    
    # Update Session State
    st.session_state['final_da_data'] = edited_da_df
    
    # Summary Metrics
    total_da = pd.to_numeric(edited_da_df['DA_Amount'], errors='coerce').sum()
    st.metric(label="Total Daily Allowance Claim", value=f"₹ {total_da:,.2f}")

    st.markdown("---")
    st.write("👉 **Next Step:** Go to '4_Export' to generate your document.")
