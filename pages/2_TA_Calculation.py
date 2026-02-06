import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import PyPDF2
import io

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Step 2: TA Calculation (AI Enhanced)")

# --- HELPER: PDF/IMAGE TEXT EXTRACTOR ---
def get_file_content(uploaded_file):
    """Converts uploaded PDF or Image to a format Gemini can understand."""
    try:
        if uploaded_file.type == "application/pdf":
            # Extract text from first few pages of PDF
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages[:3]: # Limit to first 3 pages to save tokens
                text += page.extract_text() + "\n"
            return f"Document Content ({uploaded_file.name}):\n{text}"
        else:
            # For images, we can't easily extract text in pure Python without OCR, 
            # so we will rely on Gemini Vision if passed as image, 
            # but here we return a placeholder if using text-only model.
            # *Ideally, pass the image object to Gemini Vision model.*
            return f"[Image File: {uploaded_file.name} - Visual processing required]"
    except Exception as e:
        return f"Error reading {uploaded_file.name}: {e}"

# --- HELPER: GEMINI AI EXTRACTION ---
def extract_ticket_data_with_gemini(api_key, diary_csv, file_contents):
    """
    Sends the Diary + Ticket text to Gemini to map costs to rows.
    """
    genai.configure(api_key=api_key)
    # Use Flash for speed and long context (tickets)
    model = genai.GenerativeModel('gemini-1.5-flash') 

    prompt = f"""
    You are an Accountant Assistant. I have a Tour Diary and a set of Ticket/Receipt texts.
    
    YOUR GOAL: Match the receipts to the Diary Rows and extract costs.
    
    ### TOUR DIARY DATA:
    {diary_csv}
    
    ### UPLOADED RECEIPTS/DOCUMENTS:
    {file_contents}
    
    ### INSTRUCTIONS:
    1. Look at the 'Departure Date', 'Arrival Date', 'Departure Place', and 'Arrival Place' in the Diary.
    2. Find a matching receipt in the Document Content.
    3. If found, extract:
       - 'ticket_amount': The cost of the ticket (Bus/Rail/Air).
       - 'class_travel': The class (e.g., "Sleeper", "Economy", "Ac Bus").
       - 'km': If the receipt shows distance (KM), extract it. Otherwise use 0.
    4. Return a JSON Object indexed by the "Row Index" (0, 1, 2...) of the diary.
    
    ### OUTPUT FORMAT (JSON ONLY):
    {{
      "0": {{ "ticket_amount": 500, "class_travel": "Bus", "km": 0 }},
      "2": {{ "ticket_amount": 1200, "class_travel": "Rail 2A", "km": 450 }}
    }}
    Only include rows where you found new data.
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean cleanup to get pure JSON
        json_text = response.text.replace("```json", "").replace("```", "").strip()
        return pd.read_json(io.StringIO(json_text), orient='index')
    except Exception as e:
        st.error(f"AI Extraction Failed: {e}")
        return pd.DataFrame()

# --- MAIN INITIALIZATION ---
st.title("🧮 Step 2: TA Calculation (AI-Powered)")

# 1. Check Login
if not st.session_state.get('gemini_api_key'):
    st.error("⚠️ Please login with your Gemini API Key on the Home Page.")
    st.stop()

# 2. Check Previous Step
if 'final_tour_diary' not in st.session_state:
    st.error("⚠️ Please complete 'Step 1: Tour Diary' first.")
    st.stop()

# 3. Load Diary Data (Cols 1-7, 11, 18)
diary_df = st.session_state['final_tour_diary'].copy()

# 4. Initialize TA Columns (8-13) if not present
if 'ta_calculation_df' not in st.session_state:
    # Create empty columns for the TA section
    diary_df["Class_of_Travel"] = ""        # Col 8
    diary_df["Ticket_Price_Rate"] = 0.0     # Col 9
    diary_df["Actual_Ticket_Amount"] = 0.0  # Col 10
    # KM (Col 11) might already exist from Step 1, ensure it's numeric
    if "KM" not in diary_df.columns:
        diary_df["KM"] = 0.0
    diary_df["Rate_per_KM"] = 0.0           # Col 12
    diary_df["Mileage_Total"] = 0.0         # Col 13
    
    st.session_state['ta_calculation_df'] = diary_df

df = st.session_state['ta_calculation_df']

# --- SECTION 1: UPLOADS & AI ACTION ---
with st.expander("📂 Upload Proofs (Salary Slip, Tickets, Bills)", expanded=True):
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        salary_file = st.file_uploader("1. Salary Slip (For Pay Level)", type=["pdf", "jpg", "png"])
        ticket_files = st.file_uploader("2. Travel Tickets (Bus/Rail/Air)", accept_multiple_files=True)
    with col_up2:
        st.info("💡 **AI Feature:** Upload your tickets and click the button below. Gemini will read the dates and prices and auto-fill columns 8, 9, and 10 for you!")
        
        if st.button("✨ Auto-Fill Amounts from Uploads", type="primary"):
            if not ticket_files:
                st.warning("Please upload ticket files first.")
            else:
                with st.spinner("Gemini is reading your tickets..."):
                    # 1. Prepare Text
                    all_text = ""
                    for f in ticket_files:
                        all_text += get_file_content(f) + "\n---\n"
                    
                    # 2. Call AI
                    updates_df = extract_ticket_data_with_gemini(
                        st.session_state['gemini_api_key'], 
                        df.to_csv(), 
                        all_text
                    )
                    
                    # 3. Update DataFrame
                    if not updates_df.empty:
                        for index, row in updates_df.iterrows():
                            if index in df.index:
                                df.at[index, "Ticket_Price_Rate"] = row.get('ticket_amount', 0)
                                df.at[index, "Actual_Ticket_Amount"] = row.get('ticket_amount', 0)
                                if row.get('class_travel'):
                                    df.at[index, "Class_of_Travel"] = row.get('class_travel')
                                # Update KM only if AI found a strictly better number (non-zero)
                                if row.get('km', 0) > 0:
                                    df.at[index, "KM"] = row.get('km')
                        
                        st.session_state['ta_calculation_df'] = df
                        st.success("✅ Data extracted and filled! Review below.")
                        st.rerun()
                    else:
                        st.warning("AI couldn't match specific tickets to dates. Please enter manually.")

st.divider()

# --- SECTION 2: DATA EDITOR (THE OLD CODE STRUCTURE) ---
st.subheader("2. Detailed TA Calculation")
st.markdown("Edit the **Rate**, **KM**, and **Ticket Amounts** manually below.")

column_config = {
    # --- FROZEN DIARY COLUMNS (1-7, 18) ---
    "Departure Place": st.column_config.TextColumn("1. Dep. Place", disabled=True),
    "Departure Date": st.column_config.TextColumn("2. Dep. Date", disabled=True),
    "Departure Time": st.column_config.TextColumn("3. Dep. Time", disabled=True),
    "Arrival Place": st.column_config.TextColumn("4. Arr. Place", disabled=True),
    "Arrival Date": st.column_config.TextColumn("5. Arr. Date", disabled=True),
    "Arrival Time": st.column_config.TextColumn("6. Arr. Time", disabled=True),
    "Mode of Travel": st.column_config.TextColumn("7. Mode", disabled=True),
    "Purpose": st.column_config.TextColumn("18. Purpose", disabled=True),

    # --- EDITABLE TA COLUMNS (8-13) ---
    "Class_of_Travel": st.column_config.TextColumn(
        "8. Class / Vehicle",
        help="e.g. Sleeper, AC Bus, Own Car"
    ),
    "Ticket_Price_Rate": st.column_config.NumberColumn(
        "9. Ticket Price / Rate (Rs.)",
        format="₹ %.2f",
        help="Price written on the ticket"
    ),
    "Actual_Ticket_Amount": st.column_config.NumberColumn(
        "10. Actual Ticket Total (Rs.)",
        format="₹ %.2f",
        help="Total amount claimed for this leg"
    ),
    "KM": st.column_config.NumberColumn(
        "11. KM (Extracted/Calc)",
        format="%.1f km",
        help="Distance in Kilometers"
    ),
    "Rate_per_KM": st.column_config.NumberColumn(
        "12. Rate / KM",
        format="₹ %.2f",
        help="Enter rate (e.g., 11 for Car, 0 for Bus)"
    ),
    "Mileage_Total": st.column_config.NumberColumn(
        "13. Mileage Total",
        format="₹ %.2f",
        help="Usually KM * Rate"
    )
}

# Ensure column order matches the request
display_cols = [
    "Departure Place", "Departure Date", "Departure Time",
    "Arrival Place", "Arrival Date", "Arrival Time", "Mode of Travel",
    "Class_of_Travel", "Ticket_Price_Rate", "Actual_Ticket_Amount",
    "KM", "Rate_per_KM", "Mileage_Total", 
    "Purpose"
]

# FILTER: Only show relevant columns
df_display = df[display_cols]

edited_df = st.data_editor(
    df_display,
    key="ta_editor",
    use_container_width=True,
    num_rows="fixed", # Rows controlled by Step 1
    column_config=column_config,
    hide_index=True
)

# --- RE-CALCULATE LOGIC (Preserving Manual Edits) ---
# We write the edits back to the session state
# If you want 13 to AUTO-CALCULATE based on 11*12, uncomment the next line:
# edited_df["Mileage_Total"] = edited_df["KM"] * edited_df["Rate_per_KM"]

# Merge back to main state
st.session_state['ta_calculation_df'].update(edited_df)

# --- TOTALS SECTION ---
st.divider()
total_ticket = edited_df["Actual_Ticket_Amount"].sum()
total_mileage = edited_df["Mileage_Total"].sum()
grand_total = total_ticket + total_mileage

c1, c2, c3 = st.columns(3)
c1.metric("🎫 Ticket Total (Col 10)", f"₹ {total_ticket:,.2f}")
c2.metric("🚗 Mileage Total (Col 13)", f"₹ {total_mileage:,.2f}")
c3.metric("💰 GRAND TOTAL", f"₹ {grand_total:,.2f}")
