import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Step 2: TA Calculation")

# --- HELPER: LOGIC TO PRE-FILL (BUT NOT FORCE) VALUES ---
def calculate_initial_values(row):
    """
    Sets up the initial columns (7-13) based on the Diary.
    Unlike the previous version, this does NOT force values to zero.
    It just provides a starting point that you can edit.
    """
    # 1. Get existing values or defaults
    mode = str(row.get("Mode of Travel", "")).lower()
    km = pd.to_numeric(row.get("KM", 0), errors='coerce')
    if pd.isna(km): km = 0.0
    
    # Default Class based on Mode string
    if "private" in mode or "car" in mode:
        class_vehicle = "Own Car / Pvt"
    elif "bus" in mode:
        class_vehicle = "Bus"
    elif "rail" in mode or "train" in mode:
        class_vehicle = "Rail"
    else:
        class_vehicle = "Other"

    # We default the Rate to 0 so you can enter it manually 
    # (since you use equivalent fare or variable rates)
    rate_per_km = 0.0
    
    # Initial Calculation
    mileage_total = km * rate_per_km
    ticket_price = 0.0 # Default to 0, user enters manual amount

    return pd.Series([
        class_vehicle,   # Col 8
        ticket_price,    # Col 9
        ticket_price,    # Col 10 (Total)
        km,              # Col 11
        rate_per_km,     # Col 12
        mileage_total    # Col 13
    ])

# --- MAIN APP UI ---

st.title("🧮 Step 2: TA Calculation (Manual Entry)")

# Check if Step 1 (Diary) was completed
if 'final_tour_diary' not in st.session_state:
    st.error("⚠️ Please complete Step 1 (Tour Diary) first.")
    st.stop()

# Get the clean diary from Page 1
diary_df = st.session_state['final_tour_diary'].copy()

# Initialize TA Calculation DataFrame if not exists
if 'ta_calculation_df' not in st.session_state:
    # Generate the initial columns (7-13)
    processed_data = diary_df.apply(lambda row: calculate_initial_values(row), axis=1)
    processed_data.columns = [
        "Class_of_Travel", "Ticket_Price_Rate", "Actual_Ticket_Amount", 
        "Kilometer", "Rate_per_KM", "Mileage_Total"
    ]
    
    # Combine original diary with new columns
    st.session_state['ta_calculation_df'] = pd.concat([diary_df, processed_data], axis=1)

# Working DF
df = st.session_state['ta_calculation_df']

# --- SECTION 1: UPLOAD EVIDENCE ---
st.subheader("1. Upload TA Documents")
col1, col2 = st.columns(2)
with col1:
    ta_tickets = st.file_uploader("Upload Tickets / Bills", accept_multiple_files=True, key="tickets")
with col2:
    ta_rules = st.file_uploader("Upload TA Rules/Statutes", accept_multiple_files=True, key="ta_rules")

if st.button("🔄 Reset Data"):
    if 'ta_calculation_df' in st.session_state:
        del st.session_state['ta_calculation_df']
    st.rerun()

st.divider()

# --- SECTION 2: DATA EDITOR (Cols 7-13) ---
st.subheader("2. Review & Edit Calculations")
st.info("💡 You can now manually edit Rates, KMs, and Ticket Amounts.")

# We use column_config to format numbers, but we leave 'disabled=False' (default)
# so you can edit the values.
edited_ta = st.data_editor(
    df,
    key="ta_editor",
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        # Freezing Diary Columns (1-6) - these come from Step 1
        "Departure Place": st.column_config.TextColumn(disabled=True),
        "Departure Date": st.column_config.TextColumn(disabled=True),
        "Departure Time": st.column_config.TextColumn(disabled=True),
        "Arrival Place": st.column_config.TextColumn(disabled=True),
        "Arrival Date": st.column_config.TextColumn(disabled=True),
        "Arrival Time": st.column_config.TextColumn(disabled=True),
        "Mode of Travel": st.column_config.TextColumn(disabled=True),
        "Purpose": st.column_config.TextColumn(disabled=True),

        # MANUAL EDIT COLUMNS (7-13)
        "Class_of_Travel": st.column_config.TextColumn(
            "8. Class / Vehicle",
            help="E.g., Own Car, Bus, Sleeper"
        ),
        
        "Ticket_Price_Rate": st.column_config.NumberColumn(
            "9. Rate/Fare (Rs.)", 
            format="₹ %.2f",
            help="Enter the Ticket Price (or Equivalent Bus Fare)"
        ),
        
        "Actual_Ticket_Amount": st.column_config.NumberColumn(
            "10. Ticket Total", 
            format="₹ %.2f", 
            help="Total Claimed (Usually same as Rate/Fare)"
        ),
        
        "Kilometer": st.column_config.NumberColumn(
            "11. KM", 
            format="%.1f km",
            help="Distance traveled"
        ),

        "Rate_per_KM": st.column_config.NumberColumn(
            "12. Rate/KM", 
            format="₹ %.2f",
            help="Enter Manual Rate if applicable (e.g. 8.00 or 11.00)"
        ),
        
        "Mileage_Total": st.column_config.NumberColumn(
            "13. Mileage Total", 
            format="₹ %.2f", 
            help="Calculate manually or enter KM * Rate"
        )
    }
)

# --- RE-CALCULATE TOTALS BASED ON USER EDITS ---
# We re-calculate the totals row-by-row to ensure accuracy if you changed Rate or KM
# If you prefer purely manual entry, you can comment these two lines out.
edited_ta["Mileage_Total"] = edited_ta["Kilometer"] * edited_ta["Rate_per_KM"]
# For tickets, we assume Total = Rate unless you manually changed Total. 
# (Here we just trust the editor output for Ticket Total to allow manual overrides)

# Save changes back to session state
st.session_state['ta_calculation_df'] = edited_ta

# --- GRAND TOTALS ---
total_ticket = edited_ta["Actual_Ticket_Amount"].sum()
total_mileage = edited_ta["Mileage_Total"].sum()
grand_total = total_ticket + total_mileage

st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("Ticket Total", f"₹ {total_ticket:,.2f}")
c2.metric("Mileage Total", f"₹ {total_mileage:,.2f}")
c3.metric("GRAND TOTAL (TA)", f"₹ {grand_total:,.2f}")
