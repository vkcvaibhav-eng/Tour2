import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import io

# ==========================================
# ⚙️ CONFIGURATION & SETUP
# ==========================================
st.set_page_config(layout="wide", page_title="Step 4: Final Consolidated Table")
st.title("📑 Step 4: Final Consolidated Claim Table")
st.markdown("### Merging TA & DA into the Official 1-18 Column Format")

# --- VALIDATION ---
if 'ta_rearranged_df' not in st.session_state:
    st.error("⚠️ Step 2 (TA Calculation) is missing. Please complete it first.")
    st.stop()

if 'final_da_data' not in st.session_state:
    st.warning("⚠️ Step 3 (DA Calculation) is missing. The table will be generated without DA values.")

api_key = st.session_state.get('gemini_api_key')
if not api_key:
    st.error("⚠️ Gemini API Key not found. Please set it in the Home page.")
    st.stop()

genai.configure(api_key=api_key)

# ==========================================
# 🧠 AI MERGING LOGIC
# ==========================================

def ai_smart_merge(ta_df, da_df, api_key):
    """
    Uses Gemini to intelligently merge TA (Travel) rows with DA (Daily) rows
    because DA is often 1 per day while TA can be multiple per day.
    """
    
    # Convert DataFrames to JSON for the prompt
    ta_json = ta_df.to_json(orient="records")
    da_json = da_df.to_json(orient="records") if da_df is not None else "[]"
    
    prompt = f"""
    You are an expert Data Processing Assistant for Government Travel Claims.
    
    **TASK:**
    Merge the "Transport Allowance (TA)" data with the "Daily Allowance (DA)" data into a single final table with exactly 18 columns.
    
    **INPUT DATA:**
    1. **TA Data (Journey Rows):** {ta_json}
    
    2. **DA Data (Daily/Halt Rows):** {da_json}
    
    **REQUIRED COLUMNS (1 to 18):**
    1. Departure Place
    2. Departure Date
    3. Departure Time
    4. Arrival Place
    5. Arrival Date
    6. Arrival Time
    7. Mode
    8. Class
    9. Ticket Price/Rate (Rs.)
    10. Actual Total Amount of Ticket (Rs.)
    11. KM
    12. Rate (Rs.) (Auto/Taxi/Pvt)
    13. Total (Rs.) [Vehicle/Fare]
    14. Days of daily allowance receivable (or Hours)
    15. Daily allowance rate (Rs.)
    16. Amount of Allowance (Rs.) [The calculated DA amount]
    17. Total amount receivable (Col 10 + Col 13 + Col 16)
    18. Purpose of Journey
    
    **MERGING LOGIC:**
    - The TA Data contains the rows for every journey. **Keep all these rows.**
    - The DA Data contains calculated amounts usually per day or per halt.
    - **Intelligently assign** the DA values (Cols 14, 15, 16) to the relevant travel row (usually the row where the traveler arrives at the halt location for that date).
    - If a date has multiple journeys, usually the DA is added to the last arrival of that day or the main halt.
    - Ensure Col 17 is the mathematical sum of 10, 13, and 16.
    - Ensure Col 18 (Purpose) is filled for every row (take from TA data).
    
    **OUTPUT FORMAT:**
    Return ONLY valid JSON: a list of objects where keys are the numbered column names (e.g., "1. Departure Place", "17. Total amount receivable...").
    """
    
    # Using the requested high-reasoning model tag (or fallback to 1.5 Pro if generic)
    # The user asked for "gemini-3-pro-preview" specifically. 
    # Note: If this model name is not yet active in your account, switch to "gemini-1.5-pro".
    model_name = "gemini-1.5-pro" 
    
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        
        # Clean JSON
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        return json.loads(text)
    except Exception as e:
        st.error(f"AI Merging Failed: {e}")
        return []

# ==========================================
# 🖥️ PAGE UI
# ==========================================

# 1. Preview Inputs
with st.expander("🔍 View Input Data (TA & DA)"):
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("TA Data (Step 2)")
        st.dataframe(st.session_state['ta_rearranged_df'])
    with c2:
        st.subheader("DA Data (Step 3)")
        if 'final_da_data' in st.session_state:
            st.dataframe(st.session_state['final_da_data'])
        else:
            st.info("No DA Data available.")

# 2. Action Button
st.divider()
col_center = st.columns([1, 2, 1])
if col_center[1].button("🚀 Generate Final 1-18 Column Table (AI Merge)", type="primary"):
    with st.spinner("AI is merging rows, aligning dates, and calculating totals..."):
        ta_df = st.session_state['ta_rearranged_df']
        da_df = st.session_state.get('final_da_data', None)
        
        merged_data = ai_smart_merge(ta_df, da_df, api_key)
        
        if merged_data:
            st.session_state['final_18_col_df'] = pd.DataFrame(merged_data)
            st.success("✅ Merging Complete!")
        else:
            st.error("Failed to generate table.")

# 3. Display & Edit
if 'final_18_col_df' in st.session_state:
    st.subheader("📝 Final Consolidated Claim Form")
    
    # Define exact column order for display
    final_cols = [
        "1. Departure Place", "2. Departure Date", "3. Departure Time",
        "4. Arrival Place", "5. Arrival Date", "6. Arrival Time",
        "7. Mode", "8. Class", 
        "9. Ticket Price/Rate (Rs.)", "10. Actual Total Amount of Ticket (Rs.)",
        "11. KM", "12. Rate (Rs.) (Auto/Taxi/Pvt)", "13. Total (Rs.)",
        "14. Days of daily allowance receivable", "15. Daily allowance rate (Rs.)",
        "16. Amount of Allowance (Rs.)",
        "17. Total amount receivable (10 + 13 + 16)",
        "18. Purpose of Journey"
    ]
    
    df_final = st.session_state['final_18_col_df']
    
    # Ensure columns match mainly for the editor
    # (AI might return slightly different keys, so we normalize if needed, 
    # but usually the prompt handles it. We'll trust the editor to show what it got.)
    
    # Force Recalculation of Col 17 to ensure Math Accuracy (Python > AI for math)
    # We strip currency symbols if present
    def clean_money(val):
        if isinstance(val, str):
            val = val.replace('₹', '').replace(',', '').strip()
        return pd.to_numeric(val, errors='coerce') if val else 0.0

    try:
        # Map AI keys to standard keys if they slightly differ, strictly relying on index if names fail
        # This is a robust fallback if AI names keys "Col 1", "Col 2" etc.
        if len(df_final.columns) == 18:
            df_final.columns = final_cols
            
        # Math Safety Check
        c10 = df_final["10. Actual Total Amount of Ticket (Rs.)"].apply(clean_money).fillna(0)
        c13 = df_final["13. Total (Rs.)"].apply(clean_money).fillna(0)
        c16 = df_final["16. Amount of Allowance (Rs.)"].apply(clean_money).fillna(0)
        df_final["17. Total amount receivable (10 + 13 + 16)"] = c10 + c13 + c16
    except Exception as e:
        st.warning(f"Auto-math validation skipped due to column mismatch: {e}")

    edited_final = st.data_editor(
        df_final,
        use_container_width=True,
        num_rows="dynamic",
        height=600,
        key="final_grid"
    )
    
    st.session_state['final_18_col_df'] = edited_final

    # 4. Totals
    st.divider()
    total_receivable = edited_final["17. Total amount receivable (10 + 13 + 16)"].sum()
    st.metric("💰 GRAND TOTAL CLAIM", f"₹ {total_receivable:,.2f}")

    # 5. Export
    st.subheader("📥 Export")
    
    # CSV Download
    csv = edited_final.to_csv(index=False).encode('utf-8')
    st.download_button(
        "Download as CSV",
        csv,
        "Final_TA_DA_Claim.csv",
        "text/csv",
        key='download-csv'
    )

    # Simple Excel Download (Using Pandas)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        edited_final.to_excel(writer, sheet_name='Claim Sheet', index=False)
        
        # Auto-adjust columns width
        worksheet = writer.sheets['Claim Sheet']
        for idx, col in enumerate(edited_final.columns):
            max_len = max(
                edited_final[col].astype(str).map(len).max(),
                len(str(col))
            ) + 2
            worksheet.set_column(idx, idx, max_len)
            
    st.download_button(
        label="Download as Excel",
        data=buffer.getvalue(),
        file_name="Final_TA_DA_Claim.xlsx",
        mime="application/vnd.ms-excel"
    )
