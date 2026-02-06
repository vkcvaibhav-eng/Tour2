import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io

# ==========================================
# ⚙️ CONFIGURATION & SETUP
# ==========================================
st.set_page_config(layout="wide", page_title="Step 2: TA Calculation (AI + Manual)")

# Get API Key from Session State (set in Home/Step 1)
api_key = st.session_state.get('gemini_api_key')

if not api_key:
    st.error("⚠️ Gemini API Key not found. Please set it in the Home page.")
    st.stop()

genai.configure(api_key=api_key)

# ==========================================
# 🧠 AI ENGINE: DOCUMENT EXTRACTION
# ==========================================
def extract_data_from_documents(uploaded_files, doc_type="ticket"):
    """
    Sends uploaded files to Gemini to extract Date, Amount, Class, and KM.
    """
    if not uploaded_files:
        return []

    results = []
    
    # Simple progress bar
    progress_bar = st.progress(0)
    
    for i, file in enumerate(uploaded_files):
        try:
            # Prepare image for Gemini
            image_data = file.getvalue()
            image_parts = [{"mime_type": file.type, "data": image_data}]
            
            # Specific Prompt based on document type
            if doc_type == "salary":
                prompt = """
                Analyze this Salary Slip. Extract the following:
                - Basic Pay Amount
                - Pay Level (or Grade Pay)
                Return ONLY valid JSON: {"basic_pay": 12345, "pay_level": "Level 11"}
                """
            else: # Tickets
                prompt = """
                Analyze this Travel Ticket/Bill. Extract:
                - Date of Travel (DD/MM/YYYY)
                - Mode/Class (e.g., 'Rail', 'Bus', 'Flight', 'Taxi')
                - Total Amount (numeric)
                - Distance/KM (if mentioned, else 0)
                
                Return ONLY valid JSON: 
                [{"date": "25/12/2025", "mode": "Bus", "amount": 540, "km": 0}]
                """

            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content([prompt, image_parts[0]])
            
            # Clean and parse JSON
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            import json
            data = json.loads(text)
            
            if isinstance(data, list):
                results.extend(data)
            else:
                results.append(data)
                
        except Exception as e:
            st.warning(f"Could not read file {file.name}: {e}")
        
        progress_bar.progress((i + 1) / len(uploaded_files))
        
    progress_bar.empty()
    return results

# ==========================================
# 📥 SECTION 1: UPLOADS & INTELLIGENCE
# ==========================================
st.title("🧮 Step 2: TA Calculation (Smart Extract)")
st.info("Upload your documents below. Gemini will read the **Ticket Rates** and **KM** and auto-fill the table for you.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Upload Salary Slip")
    salary_file = st.file_uploader("For Pay Level Validation", type=['png', 'jpg', 'jpeg', 'pdf'], key="sal_up")
    
    if salary_file and st.button("🔍 Analyze Salary Slip"):
        with st.spinner("Reading Salary Slip..."):
            data = extract_data_from_documents([salary_file], "salary")
            if data:
                st.session_state['user_salary_info'] = data[0]
                st.success(f"Detected: Basic Pay ₹{data[0].get('basic_pay')} | Level: {data[0].get('pay_level')}")

with col2:
    st.subheader("2. Upload Tickets / Bills")
    ticket_files = st.file_uploader("Train, Bus, Flight, Taxi Bills", accept_multiple_files=True, type=['png', 'jpg', 'jpeg', 'pdf'], key="tick_up")
    
    if ticket_files and st.button("🤖 Extract Ticket Data"):
        with st.spinner("Gemini is reading your tickets..."):
            extracted_tickets = extract_data_from_documents(ticket_files, "ticket")
            st.session_state['extracted_tickets'] = extracted_tickets
            st.success(f"Successfully extracted data from {len(extracted_tickets)} tickets!")
            st.json(extracted_tickets, expanded=False)

st.divider()

# ==========================================
# 🗓️ SECTION 2: THE "OLD CODE" CALCULATOR
# ==========================================
st.header("3. Review & Edit Calculations")

# 1. Load Diary Data
if 'final_tour_diary' not in st.session_state:
    st.error("⚠️ Please complete Step 1 (Tour Diary) first.")
    st.stop()

df = st.session_state['final_tour_diary'].copy()

# 2. Logic to Merge Extracted Data into Diary
def smart_prefill(row):
    # Default Values
    mode = str(row.get("Mode of Travel", "")).lower()
    diary_date = str(row.get("Departure Date", ""))
    
    # Defaults
    class_travel = "Other"
    ticket_price = 0.0
    km = pd.to_numeric(row.get("KM", 0), errors='coerce')
    if pd.isna(km): km = 0.0
    rate_per_km = 0.0
    
    # A. Mode Detection
    if "private" in mode or "car" in mode:
        class_travel = "Own Car / Pvt"
        # Often rate is manual for car
    elif "bus" in mode:
        class_travel = "Bus / ST"
    elif "rail" in mode or "train" in mode:
        class_travel = "Rail"
    elif "flight" in mode or "air" in mode:
        class_travel = "Air"
    
    # B. INTELLIGENCE MERGE (Check extracted tickets)
    found_ticket = False
    if 'extracted_tickets' in st.session_state:
        for t in st.session_state['extracted_tickets']:
            # Fuzzy Date Match (Simple string match for now)
            if t.get('date') in diary_date or diary_date in t.get('date', ''):
                # If modes loosely match
                t_mode = t.get('mode', '').lower()
                if (("bus" in t_mode and "bus" in mode) or 
                    ("rail" in t_mode and "rail" in mode) or
                    ("flight" in t_mode and "flight" in mode)):
                    
                    ticket_price = float(t.get('amount', 0))
                    class_travel = t.get('mode', class_travel)
                    
                    # If ticket has KM (e.g. Taxi bill), overwrite KM
                    if t.get('km', 0) > 0:
                        km = float(t.get('km'))
                    
                    found_ticket = True
                    break
    
    # C. Calculation Logic (Standard)
    actual_total = ticket_price # Assuming 1 ticket per row usually
    mileage_total = km * rate_per_km

    return pd.Series([
        class_travel,   # Col 8
        ticket_price,   # Col 9
        actual_total,   # Col 10
        km,             # Col 11 (Refilled)
        rate_per_km,    # Col 12
        mileage_total   # Col 13
    ])

# 3. Apply Logic (Only if not already edited)
if 'ta_calculation_df' not in st.session_state:
    processed_cols = df.apply(smart_prefill, axis=1)
    processed_cols.columns = [
        "Class_of_Travel", "Ticket_Price_Rate", "Actual_Ticket_Amount", 
        "Kilometer", "Rate_per_KM", "Mileage_Total"
    ]
    # Update the KM in the diary with the one potentially found in tickets
    # (Optional: depends if you want strict Diary KM or Ticket KM. Here we prioritize Ticket KM for TA)
    
    st.session_state['ta_calculation_df'] = pd.concat([df, processed_cols], axis=1)

# Allow Reset to re-trigger intelligence
if st.button("🔄 Reload & Merge Extracted Data"):
    del st.session_state['ta_calculation_df']
    st.rerun()

current_df = st.session_state['ta_calculation_df']

# 4. The "Old Code" Data Editor
st.markdown("### 📝 Edit Details (Columns 8-13)")
st.caption("You can manually change any value extracted by the AI.")

edited_ta = st.data_editor(
    current_df,
    key="ta_editor_main",
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        # --- FROZEN DIARY COLUMNS (1-7 + 18) ---
        "Departure Place": st.column_config.TextColumn("1. Departure", disabled=True),
        "Departure Date": st.column_config.TextColumn("2. Date", disabled=True),
        "Departure Time": st.column_config.TextColumn("3. Time", disabled=True),
        "Arrival Place": st.column_config.TextColumn("4. Arrival", disabled=True),
        "Arrival Date": st.column_config.TextColumn("5. Date", disabled=True),
        "Arrival Time": st.column_config.TextColumn("6. Time", disabled=True),
        "Mode of Travel": st.column_config.TextColumn("7. Mode", disabled=True),
        "Purpose": st.column_config.TextColumn("18. Purpose", disabled=True),

        # --- THE TA CALCULATION COLUMNS (8-13) ---
        "Class_of_Travel": st.column_config.TextColumn(
            "8. Class of Travel",
            help="E.g. Rail 2nd AC, Volvo Bus, Own Car"
        ),
        
        "Ticket_Price_Rate": st.column_config.NumberColumn(
            "9. Ticket Price/Rate (Rs.)",
            format="₹ %.2f",
            help="Extracted from Ticket or Manual Entry"
        ),
        
        "Actual_Ticket_Amount": st.column_config.NumberColumn(
            "10. Actual Total Amount",
            format="₹ %.2f",
            help="Total amount claimed for ticket"
        ),
        
        "Kilometer": st.column_config.NumberColumn(
            "11. KM",
            format="%.1f",
            help="Extracted from Diary or Taxi Bill"
        ),
        
        "Rate_per_KM": st.column_config.NumberColumn(
            "12. Rate/KM",
            format="₹ %.2f",
            help="Manual Rate (e.g., 11 for Car)"
        ),
        
        "Mileage_Total": st.column_config.NumberColumn(
            "13. Mileage Total",
            format="₹ %.2f",
            disabled=True, # Auto-calculated
            help="KM * Rate"
        )
    }
)

# 5. Live Calculation (React to manual edits)
# Recalculate Mileage Total based on KM * Rate
edited_ta["Mileage_Total"] = edited_ta["Kilometer"] * edited_ta["Rate_per_KM"]

# If Ticket Amount is 0 but Rate is > 0, assume Amount = Rate (Helper logic)
# (User can still manually override Col 10 if needed, but we default it for convenience)
edited_ta.loc[(edited_ta["Actual_Ticket_Amount"] == 0) & (edited_ta["Ticket_Price_Rate"] > 0), "Actual_Ticket_Amount"] = edited_ta["Ticket_Price_Rate"]

# Update Session State
st.session_state['ta_calculation_df'] = edited_ta

# 6. Grand Totals
total_ticket = edited_ta["Actual_Ticket_Amount"].sum()
total_mileage = edited_ta["Mileage_Total"].sum()
grand_total = total_ticket + total_mileage

st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("🎫 Ticket Total", f"₹ {total_ticket:,.2f}")
c2.metric("🚗 Mileage Total", f"₹ {total_mileage:,.2f}")
c3.metric("💰 GRAND TOTAL", f"₹ {grand_total:,.2f}")
