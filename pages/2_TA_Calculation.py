import streamlit as st
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Step 2: TA Calculation (Manual + AI Rules)")

# --- INTELLIGENCE: USER CONTEXT ---
# Extracted from your uploaded Salary Slip & Tour Diary
USER_BASIC_PAY = 79800.0  
PAY_LEVEL = 11            # Implied from 79800 scale
OFFICIAL_CAR_RATE = 11.0  # Gujarat Govt Rate for Level 11
OFFICIAL_BIKE_RATE = 2.0  # Standard lower rate

# --- HELPER: LOGIC TO PRE-FILL (BUT NOT FORCE) VALUES ---
def calculate_initial_values(row):
    """
    Sets up the initial columns (7-13) based on the Diary.
    All values are left EDITABLE for the user.
    """
    # 1. Get existing values or defaults from previous steps
    mode = str(row.get("Mode of Travel", "")).lower()
    km = pd.to_numeric(row.get("KM", 0), errors='coerce')
    if pd.isna(km): km = 0.0
    
    # 2. Smart Detection of Class
    if "private" in mode or "car" in mode:
        class_vehicle = "Own Car (Petrol)"
        # University Rule Nuance: Often uses Bus Fare, but we set Rate to 0 to let user decide
        default_rate = 0.0 
    elif "motor" in mode or "bike" in mode:
        class_vehicle = "Motor Cycle"
        default_rate = 0.0
    elif "bus" in mode:
        class_vehicle = "Bus / ST"
        default_rate = 0.0
    elif "rail" in mode:
        class_vehicle = "Rail / Train"
        default_rate = 0.0
    else:
        class_vehicle = "Other"

    # 3. Initial Math (User can override these)
    ticket_price = 0.0 
    mileage_total = km * default_rate

    return pd.Series([
        class_vehicle,   # Col 8
        ticket_price,    # Col 9 (Rate/Fare)
        ticket_price,    # Col 10 (Total Ticket)
        km,              # Col 11 (KM)
        default_rate,    # Col 12 (Rate/KM)
        mileage_total    # Col 13 (Total Mileage)
    ])

# --- HELPER: AI JUSTIFICATION ENGINE ---
def generate_ai_justification(row):
    """
    Checks the user's manual entry against Gujarat Civil Services Rules.
    Returns a status string.
    """
    mode = str(row.get("Mode of Travel", "")).lower()
    claimed_ticket = row.get("Actual_Ticket_Amount", 0)
    claimed_mileage = row.get("Mileage_Total", 0)
    total_claim = claimed_ticket + claimed_mileage
    
    km = row.get("Kilometer", 0)
    
    # RULE CHECK: PRIVATE VEHICLE
    if "private" in mode or "car" in mode:
        # Calculate what the Govt Rule theoretically allows (Level 11 @ ₹11/km)
        rule_entitlement = km * OFFICIAL_CAR_RATE
        
        if total_claim == 0:
            return "⚠️ Missing Amount"
        elif total_claim <= rule_entitlement:
            return "✅ OK (Within Govt Limit)"
        else:
            diff = total_claim - rule_entitlement
            return f"⚠️ Claim exceeds Govt Rate by ₹{diff:.0f}. Justification required."

    # RULE CHECK: PUBLIC TRANSPORT
    elif "bus" in mode or "rail" in mode:
        if km > 0 and claimed_mileage > 0:
             return "❓ Verify: Mileage claimed for Public Transport?"
        return "✅ Standard Fare"
        
    return "ℹ️ Manual Entry"

# --- MAIN APP UI ---

st.title("🧮 Step 2: TA Calculation (Manual Entry)")
st.caption(f"User: Vaibhavkumar (Level {PAY_LEVEL}) | Official Car Rate: ₹{OFFICIAL_CAR_RATE}/km")

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
with st.expander("📂 Upload TA Documents (Tickets/Rules)", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        ta_tickets = st.file_uploader("Upload Tickets", accept_multiple_files=True, key="tickets")
    with col2:
        ta_rules = st.file_uploader("Upload Rules", accept_multiple_files=True, key="ta_rules")

if st.button("🔄 Reset to Defaults"):
    if 'ta_calculation_df' in st.session_state:
        del st.session_state['ta_calculation_df']
    st.rerun()

st.divider()

# --- SECTION 2: DATA EDITOR (Cols 7-13) ---
st.subheader("2. Review & Edit Calculations")
st.markdown("**Instructions:** Enter your *Ticket Price* OR *KM & Rate* manually. The AI will audit your claim below.")

# We use column_config to format numbers, but we leave 'disabled=False' (default)
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

        # MANUAL EDIT COLUMNS (7-13) - ALL EDITABLE
        "Class_of_Travel": st.column_config.TextColumn(
            "8. Class / Vehicle",
            help="E.g., Own Car, Bus, Sleeper"
        ),
        
        "Ticket_Price_Rate": st.column_config.NumberColumn(
            "9. Rate/Fare (Rs.)", 
            format="₹ %.2f",
            help="Enter Ticket Price OR Equivalent Bus Fare for Car"
        ),
        
        "Actual_Ticket_Amount": st.column_config.NumberColumn(
            "10. Ticket Total", 
            format="₹ %.2f", 
            help="Usually same as Rate/Fare"
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
            help="Calculated as KM * Rate (Manual Override Allowed)"
        )
    }
)

# --- RE-CALCULATE TOTALS ---
# We force the math to ensure totals are correct based on your manual inputs
# IF you want the code to calculate 13 based on 11*12, keep this line:
edited_ta["Mileage_Total"] = edited_ta["Kilometer"] * edited_ta["Rate_per_KM"]
# If you want to type Mileage Total manually without math, delete the line above.

st.session_state['ta_calculation_df'] = edited_ta

# --- SECTION 3: AI RULE AUDIT ---
st.subheader("🤖 AI Compliance Audit")
st.info("The AI checks your manual entries against your Salary Level (11) and Gujarat Govt Rules.")

# Create Audit Dataframe
audit_df = edited_ta[["Departure Date", "Mode of Travel", "Actual_Ticket_Amount", "Mileage_Total", "Kilometer"]].copy()
audit_df["Total Claim"] = audit_df["Actual_Ticket_Amount"] + audit_df["Mileage_Total"]
# Apply AI Logic
audit_df["AI Justification"] = audit_df.apply(lambda row: generate_ai_justification(row), axis=1)

# Display Audit (Style the remarks)
st.dataframe(
    audit_df[["Departure Date", "Mode of Travel", "Total Claim", "AI Justification"]],
    use_container_width=True,
    hide_index=True
)

# --- GRAND TOTALS ---
total_ticket = edited_ta["Actual_Ticket_Amount"].sum()
total_mileage = edited_ta["Mileage_Total"].sum()
grand_total = total_ticket + total_mileage

st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("Ticket Total", f"₹ {total_ticket:,.2f}")
c2.metric("Mileage Total", f"₹ {total_mileage:,.2f}")
c3.metric("GRAND TOTAL (TA)", f"₹ {grand_total:,.2f}")
