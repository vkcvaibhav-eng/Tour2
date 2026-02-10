import streamlit as st
import pandas as pd
import json
import google.generativeai as genai
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Step 3: DA Calculation")
st.title("💰 Step 3: Daily Allowance (DA) Calculation")
st.markdown("### Based on Statute S.119 (Gujarat Agricultural Universities)")

# --- 1. SETUP & VALIDATION ---
if 'raw_diary_df' not in st.session_state or st.session_state['raw_diary_df'].empty:
    st.warning("⚠️ No Tour Diary found. Please complete 'Step 1: Tour Diary' first.")
    st.stop()

api_key = st.session_state.get('gemini_api_key')
if not api_key:
    st.error("⚠️ Gemini API Key missing. Please set it in 'Home'.")
    st.stop()

# --- 2. USER INPUTS FOR RATES ---
st.sidebar.header("Configuration")
st.sidebar.info("Statute S.119 requires your applicable Daily Allowance rate.")

# User inputs their eligible rate per day
da_rate_ordinary = st.sidebar.number_input(
    "Ordinary DA Rate (₹)", 
    min_value=0, 
    value=500, 
    help="Your eligible DA for ordinary places."
)

da_rate_hotel = st.sidebar.number_input(
    "Hotel/Special DA Rate (₹)", 
    min_value=0, 
    value=1000, 
    help="Your eligible DA for Hotel stays or Tier-1 Cities."
)

# --- 3. STATUTE S.119 LOGIC CONTEXT ---
# We embed the rules directly so the AI knows how to calculate strict S.119 compliance
S119_RULES_CONTEXT = """
**STATUTE S.119 DA CALCULATION RULES:**

1. **Absence Definition**: Absence from Headquarters is calculated from the time of departure to the time of return.
2. **Day Definition**: A "Day" means a calendar day (00:00 to 24:00).
3. **Rates based on Duration (Per Day):**
   - Absence not exceeding 6 hours: **30%** of Daily Allowance.
   - Absence exceeding 6 hours but not exceeding 12 hours: **50%** of Daily Allowance.
   - Absence exceeding 12 hours: **100%** of Daily Allowance.
4. **City Tiers (Tier-1/Special):**
   - Cities like Ahmedabad, Surat, Vadodara, Rajkot, Bhavnagar, Jamnagar, Mumbai, Delhi, Chennai, Bangalore, Kolkata, Hyderabad, Pune, Jaipur, etc., are considered for Higher Rates/Hotel Rates if applicable.
   - All other places: Ordinary Rate.
"""

# --- 4. CALCULATION ENGINE ---
st.subheader("1. Generate Calculation")

col1, col2 = st.columns([1, 4])
if col1.button("🤖 Calculate DA with AI"):
    with st.spinner("Applying S.119 Rules to your Tour Diary..."):
        try:
            # Prepare Data
            diary_json = st.session_state['raw_diary_df'].to_json(orient='records', date_format='iso')
            
            # Construct Prompt
            prompt = f"""
            You are an accountant for an Agricultural University in Gujarat. 
            Calculate the Daily Allowance (DA) for the following Tour Diary based strictly on Statute S.119.

            **INPUT DATA (Tour Diary):**
            {diary_json}

            **USER RATES:**
            - Ordinary Rate (100%): ₹{da_rate_ordinary}
            - Special/Hotel Rate (100%): ₹{da_rate_hotel}

            **RULES (Statute S.119):**
            {S119_RULES_CONTEXT}

            **INSTRUCTIONS:**
            1. Analyze the tour row by row. Determine the "Place of Halt" for each day.
            2. If the place is a major city (Ahmedabad, Surat, Mumbai, Delhi, Bangalore, etc.), use the **Special Rate**. Otherwise, use **Ordinary Rate**.
            3. Calculate the hours spent on tour for each specific date.
            4. Apply the Percentage Rule (30% / 50% / 100%) based on hours.
            5. Return a JSON array.

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

            # Call Gemini
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-3-flash-preview')
            response = model.generate_content(prompt)
            
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
    st.subheader("2. Review & Edit DA Claims")
    st.markdown("You can modify the percentage or amounts manually if the AI miscategorized a city.")
    
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
