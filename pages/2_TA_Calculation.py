import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Step 2: TA Calculation (Automated)")

# --- USER CONSTANTS (Extracted from your Salary Slip & Rules) ---
USER_BASIC_PAY = 79800.0  # From Salary Slip
PAY_LEVEL = 11            # Implied from 79800 scale (Level 11 starts ~67700)
# Gujarat Govt Rule 2024 / University Norms for Own Car
MILEAGE_RATE_CAR = 11.0   # Standard Rate for Petrol Car
# DA Rates for Level 11 (Ref: Revised TD/DA 2024)
DA_RATES = {
    "Ordinary": {"X": 900, "Y": 700, "Z": 400},
    "Hotel":    {"X": 2000, "Y": 1600, "Z": 900}
}

def get_da_rate(city_class="Z", stay_type="Ordinary"):
    """Returns the full DA rate based on Pay Level 11 rules."""
    return DA_RATES.get(stay_type, DA_RATES["Ordinary"]).get(city_class, 400)

def calculate_allowance_logic(row):
    """
    The 'Brain' of the script. 
    Calculates Columns 7-13 automatically based on Mode and Time.
    """
    # 1. Parse Times
    try:
        fmt = "%d/%m/%Y %H:%M"
        dep_str = f"{row['Departure Date']} {row['Departure Time']}"
        arr_str = f"{row['Arrival Date']} {row['Arrival Time']}"
        t1 = datetime.strptime(dep_str, fmt)
        t2 = datetime.strptime(arr_str, fmt)
        duration_hrs = (t2 - t1).total_seconds() / 3600.0
    except:
        duration_hrs = 0.0

    # 2. Mileage Logic (Cols 11, 12, 13)
    # If Mode is Private Vehicle, auto-calc mileage
    mode = str(row.get("Mode of Travel", "")).lower()
    km = pd.to_numeric(row.get("KM", 0), errors='coerce')
    if pd.isna(km): km = 0.0

    rate_per_km = 0.0
    mileage_total = 0.0
    ticket_price = pd.to_numeric(row.get("Ticket_Price_Rate", 0), errors='coerce')
    if pd.isna(ticket_price): ticket_price = 0.0
    
    # Logic: Private Vehicle gets Mileage, Public Transport gets Ticket
    if "private" in mode or "car" in mode:
        rate_per_km = MILEAGE_RATE_CAR
        mileage_total = km * rate_per_km
        # Clear ticket price if user accidentally entered it for car
        ticket_price = 0.0
        class_vehicle = "Own Car (Petrol)"
    elif "bus" in mode or "rail" in mode:
        rate_per_km = 0.0
        mileage_total = 0.0
        # Ticket price is manual, but we ensure mileage is 0
        class_vehicle = "Public Transport"
    else:
        class_vehicle = "Other"

    # 3. DA Calculation Logic (Hidden Intelligence)
    # Rules: <6 hr = 30%, 6-12 hr = 50%, >12 hr = 100%
    # We default to 'Z' class city unless specified.
    full_da_rate = get_da_rate("Z", "Ordinary") 
    
    if duration_hrs < 6:
        da_percentage = 0.3
    elif duration_hrs < 12:
        da_percentage = 0.5
    else:
        da_percentage = 1.0
        
    da_amount = full_da_rate * da_percentage

    return pd.Series([
        class_vehicle,   # Col 8
        ticket_price,    # Col 9
        ticket_price,    # Col 10 (Total)
        km,              # Col 11
        rate_per_km,     # Col 12
        mileage_total,   # Col 13
        da_amount        # Extra: Auto-calc DA
    ])


# --- MAIN APP UI ---

st.title("🧮 Step 2: TA Calculation (Automated)")
st.caption(f"User Profile: Level {PAY_LEVEL} | Basic: ₹{USER_BASIC_PAY} | Mileage Rate: ₹{MILEAGE_RATE_CAR}/km")

# Check if Step 1 (Diary) was completed
if 'final_tour_diary' not in st.session_state:
    st.error("⚠️ Please complete Step 1 (Tour Diary) first.")
    st.stop()

# Get the clean diary from Page 1
diary_df = st.session_state['final_tour_diary'].copy()

# Initialize TA Calculation DataFrame if not exists
if 'ta_calculation_df' not in st.session_state:
    # --- INTELLIGENT INITIALIZATION ---
    # We apply the logic rules immediately upon loading
    processed_data = diary_df.apply(lambda row: calculate_allowance_logic(row), axis=1)
    processed_data.columns = [
        "Class_of_Travel", "Ticket_Price_Rate", "Actual_Ticket_Amount", 
        "Kilometer", "Rate_per_KM", "Mileage_Total", "Calculated_DA"
    ]
    
    # Combine original diary with calculated columns
    st.session_state['ta_calculation_df'] = pd.concat([diary_df, processed_data], axis=1)

# Working DF
df = st.session_state['ta_calculation_df']

# --- SECTION 1: UPLOAD EVIDENCE & RULES ---
st.subheader("1. Upload TA Documents")
col1, col2 = st.columns(2)
with col1:
    ta_tickets = st.file_uploader("Upload Tickets / Bills", accept_multiple_files=True, key="tickets")
with col2:
    ta_rules = st.file_uploader("Upload TA Rules/Statutes", accept_multiple_files=True, key="ta_rules")

if st.button("🔄 Recalculate Rules"):
    # Re-apply the logic engine
    processed_data = df.apply(lambda row: calculate_allowance_logic(row), axis=1)
    # Update only the calculated columns
    df.update(processed_data)
    st.session_state['ta_calculation_df'] = df
    st.success("Rules re-applied based on 2024 Provisions!")
    st.rerun()

st.divider()

# --- SECTION 2: DATA EDITOR (Cols 7-13) ---
st.subheader("2. Review & Edit Calculations")
st.info("💡 Columns 8-13 have been auto-calculated based on your Salary Level & Gujarat Govt Rules.")

edited_ta = st.data_editor(
    df,
    key="ta_editor",
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        # Freezing Diary Columns (1-6)
        "Departure Place": st.column_config.TextColumn(disabled=True),
        "Departure Date": st.column_config.TextColumn(disabled=True),
        "Departure Time": st.column_config.TextColumn(disabled=True),
        "Arrival Place": st.column_config.TextColumn(disabled=True),
        "Arrival Date": st.column_config.TextColumn(disabled=True),
        "Arrival Time": st.column_config.TextColumn(disabled=True),
        "Mode of Travel": st.column_config.TextColumn(disabled=True),
        "Purpose": st.column_config.TextColumn(disabled=True),

        # AUTOMATED COLUMNS (7-13)
        "Class_of_Travel": st.column_config.TextColumn(
            "8. Class / Vehicle",
            help="Auto-detected: Own Car or Public Transport"
        ),
        
        "Ticket_Price_Rate": st.column_config.NumberColumn(
            "9. Rate/Fare (Rs.)", 
            format="₹ %.2f",
            help="Enter Bus/Train Ticket Price here"
        ),
        
        "Actual_Ticket_Amount": st.column_config.NumberColumn(
            "10. Ticket Total", 
            format="₹ %.2f", 
            disabled=True, # Auto-sum
            help="Total Claimed for Ticket"
        ),
        
        "Kilometer": st.column_config.NumberColumn(
            "11. KM", 
            format="%.1f km",
            help="Enter distance for Road Mileage"
        ),

        "Rate_per_KM": st.column_config.NumberColumn(
            "12. Rate/KM", 
            format="₹ %.2f",
            disabled=True, # Locked to Rule
            help=f"Fixed at ₹{MILEAGE_RATE_CAR} for Private Car (Level 11)"
        ),
        
        "Mileage_Total": st.column_config.NumberColumn(
            "13. Mileage Total", 
            format="₹ %.2f", 
            disabled=True, # Auto-calc
            help="Calculated as KM * Rate"
        ),
        
        "Calculated_DA": st.column_config.NumberColumn(
            "Auto DA (Ref)",
            format="₹ %.0f",
            disabled=True,
            help="System estimate of DA based on hours"
        )
    }
)

# Save changes back to session state
st.session_state['ta_calculation_df'] = edited_ta

# --- TOTALS ---
total_ticket = edited_ta["Actual_Ticket_Amount"].sum()
total_mileage = edited_ta["Mileage_Total"].sum()
total_da = edited_ta["Calculated_DA"].sum()
grand_total = total_ticket + total_mileage + total_da

st.divider()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Ticket Total", f"₹ {total_ticket:,.2f}")
c2.metric("Mileage Total", f"₹ {total_mileage:,.2f}")
c3.metric("Estimated DA", f"₹ {total_da:,.2f}")
c4.metric("GRAND TOTAL", f"₹ {grand_total:,.2f}")
