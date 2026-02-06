import streamlit as st
import pandas as pd
import json

st.set_page_config(layout="wide")
st.title("🧮 Step 2: TA Calculation")

# Check if Step 1 (Diary) was completed
if 'final_tour_diary' not in st.session_state:
    st.error("⚠️ Please complete Step 1 (Tour Diary) first.")
    st.stop()

# Get the clean diary from Page 1
diary_df = st.session_state['final_tour_diary']

# --- SECTION 1: UPLOAD EVIDENCE & RULES ---
st.subheader("1. Upload TA Documents")
st.markdown("Upload your tickets and specific Statutes/Rules if applicable.")

col1, col2 = st.columns(2)
with col1:
    ta_tickets = st.file_uploader("Upload Tickets / Bills", accept_multiple_files=True, key="tickets")
with col2:
    ta_rules = st.file_uploader("Upload TA Rules/Statutes", accept_multiple_files=True, key="ta_rules")

if st.button("🔄 Apply Rules & Reset Data"):
    # This force-clears the old data to prevent conflicts
    if 'ta_calculation_df' in st.session_state:
        del st.session_state['ta_calculation_df']
    st.success("Data reset! Logic re-applied.")
    st.rerun()

st.divider()

# =========================================================
# SECTION 2: INITIALIZATION & SELF-HEALING (FIX FOR KEYERROR)
# =========================================================

# --- HELPER: RETRIEVE KM FROM RAW DATA ---
def try_get_km_from_raw(dep_date, dep_place):
    raw_data = st.session_state.get('extracted_data', {})
    if isinstance(raw_data, str):
        try:
            if "```json" in raw_data: raw_data = json.loads(raw_data.split("```json")[1].split("```")[0])
            elif "```" in raw_data: raw_data = json.loads(raw_data.split("```")[1].split("```")[0])
            else: raw_data = json.loads(raw_data)
        except: return 0.0

    if isinstance(raw_data, dict):
        tour_list = raw_data.get("tour_diary", [])
        for item in tour_list:
            raw_place = str(item.get("Departure_Place", "")).strip().lower()
            target_place = str(dep_place).strip().lower()
            if raw_place in target_place or target_place in raw_place:
                val = item.get("KM") or item.get("Distance") or item.get("Kilometer")
                if val:
                    try: return float(str(val).replace("km", "").strip())
                    except: pass
    return 0.0

# 1. Initialize if missing
if 'ta_calculation_df' not in st.session_state:
    # Prepare basic columns 1-7 from Diary
    req_cols = ["Departure_Place", "Departure_Date", "Departure_Time", 
                "Arrival_Place", "Arrival_Date", "Arrival_Time", 
                "Mode_of_Travel", "Purpose"]
    for c in req_cols:
        if c not in diary_df.columns: diary_df[c] = None
    
    ta_df = diary_df.copy()
    st.session_state['ta_calculation_df'] = ta_df

# 2. SELF-HEALING: Fix Columns if they are missing or named differently
# This prevents the KeyError "Ticket_Price_Rate"
df = st.session_state['ta_calculation_df']

# Rename old columns to new names if they exist
if "Ticket_Price" in df.columns and "Ticket_Price_Rate" not in df.columns:
    df = df.rename(columns={"Ticket_Price": "Ticket_Price_Rate"})
if "Total_Amount" in df.columns and "Actual_Ticket_Amount" not in df.columns:
    df = df.rename(columns={"Total_Amount": "Actual_Ticket_Amount"})

# Ensure all 13 columns exist
required_cols = {
    "Class_of_Travel": "Ordinary",
    "Ticket_Price_Rate": 0.0,
    "Actual_Ticket_Amount": 0.0,
    "Kilometer": 0.0,
    "Rate_per_KM": 0.0,
    "Mileage_Total": 0.0
}

for col, default_val in required_cols.items():
    if col not in df.columns:
        df[col] = default_val

# Re-Apply Logic for Class/Vehicle
df["Class_of_Travel"] = df.apply(
    lambda x: "Govt. Vehicle" if "University" in str(x.get("Mode_of_Travel", "")) or "Govt" in str(x.get("Mode_of_Travel", "")) else x.get("Class_of_Travel", "Ordinary"), 
    axis=1
)

# Intelligent KM Extraction (if still 0)
for idx, row in df.iterrows():
    mode = str(row.get("Mode_of_Travel", "")).lower()
    if ("private" in mode or "university" in mode) and df.at[idx, "Kilometer"] == 0:
        # Check diary original
        if "KM" in diary_df.columns and pd.notnull(diary_df.loc[idx, "KM"]):
             try: df.at[idx, "Kilometer"] = float(diary_df.loc[idx, "KM"])
             except: pass
        # Check raw AI data
        if df.at[idx, "Kilometer"] == 0:
             df.at[idx, "Kilometer"] = try_get_km_from_raw(row.get("Departure_Date"), row.get("Departure_Place"))

st.session_state['ta_calculation_df'] = df

# =========================================================
# SECTION 3: SMART FILL SYSTEM
# =========================================================
df = st.session_state['ta_calculation_df']

# Identify Rows needing info
pvt_mask = df["Mode_of_Travel"].str.contains("Private|Car|Jeep", case=False, na=False)
missing_pvt_fare = df[pvt_mask & (df["Ticket_Price_Rate"] == 0)]

auto_mask = df["Mode_of_Travel"].str.contains("Auto|Rickshaw", case=False, na=False)
missing_auto_data = df[auto_mask & ((df["Kilometer"] == 0) | (df["Rate_per_KM"] == 0))]

pub_mask = df["Mode_of_Travel"].str.contains("Bus|Rail|Train|Flight|Air|Taxi", case=False, na=False)
missing_pub_fare = df[pub_mask & (df["Ticket_Price_Rate"] == 0)]

attention_needed = missing_pvt_fare.index.union(missing_auto_data.index).union(missing_pub_fare.index)

if not attention_needed.empty:
    st.warning(f"⚠️ Found {len(attention_needed)} items needing manual input (Fares or Distances).")
    
    with st.expander("📝 Smart Fill: Add Missing Details", expanded=True):
        st.caption("Fill details here to auto-update the main table.")
        pending_df = df.loc[attention_needed, ["Departure_Place", "Arrival_Place", "Mode_of_Travel"]].drop_duplicates()
        
        for i, row in pending_df.iterrows():
            dep, arr, mode = row["Departure_Place"], row["Arrival_Place"], str(row["Mode_of_Travel"])
            
            # Match current row
            current_match = df[(df["Departure_Place"] == dep) & (df["Arrival_Place"] == arr) & (df["Mode_of_Travel"] == mode)].iloc[0]
            
            is_pvt = "Private" in mode or "Car" in mode
            is_auto = "Auto" in mode or "Rickshaw" in mode
            is_pub = not (is_pvt or is_auto) and "University" not in mode
            
            c1, c2, c3, c4 = st.columns([2.5, 1.5, 1.5, 1])
            with c1:
                st.write(f"**{dep}** ➝ **{arr}**")
                st.caption(f"via {mode}")
            
            km_val = 0.0
            with c2:
                if (is_pvt or is_auto) and current_match["Kilometer"] == 0:
                    km_val = st.number_input(f"Distance (KM)", min_value=0.0, key=f"km_{i}")
                elif current_match["Kilometer"] > 0:
                    st.success(f"KM: {current_match['Kilometer']}")
                else:
                    st.write("---")

            fare_val, rate_km_val = 0.0, 0.0
            with c3:
                if is_pvt and current_match["Ticket_Price_Rate"] == 0:
                    fare_val = st.number_input(f"Bus Fare Equiv.", min_value=0.0, key=f"fare_{i}")
                elif is_auto and current_match["Rate_per_KM"] == 0:
                    rate_km_val = st.number_input(f"Rate/KM", value=12.0, key=f"rate_{i}")
                elif is_pub and current_match["Ticket_Price_Rate"] == 0:
                    fare_val = st.number_input(f"Ticket Price", min_value=0.0, key=f"fare_{i}")
                elif current_match["Ticket_Price_Rate"] > 0:
                    st.success(f"Fare: {current_match['Ticket_Price_Rate']}")
                else:
                    st.write("---")
            
            with c4:
                if st.button("Apply", key=f"btn_{i}"):
                    mask = (df["Departure_Place"] == dep) & (df["Arrival_Place"] == arr) & (df["Mode_of_Travel"] == mode)
                    if km_val > 0: st.session_state['ta_calculation_df'].loc[mask, "Kilometer"] = km_val
                    if fare_val > 0: st.session_state['ta_calculation_df'].loc[mask, "Ticket_Price_Rate"] = fare_val
                    if rate_km_val > 0: st.session_state['ta_calculation_df'].loc[mask, "Rate_per_KM"] = rate_km_val
                    st.rerun()

# =========================================================
# SECTION 4: AUTO CALCULATION & MATRIX (Cols 1-13)
# =========================================================
st.subheader("2. TA Calculation Matrix")

# Apply Calculations
for index, row in st.session_state['ta_calculation_df'].iterrows():
    mode = str(row["Mode_of_Travel"]).lower()
    
    # 1. Uni Vehicle (All 0)
    if "university" in mode or ("govt" in mode and "private" not in mode):
         st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = 0.0
         st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0
         st.session_state['ta_calculation_df'].at[index, "Ticket_Price_Rate"] = 0.0
    
    # 2. Private Car (Fare = Col 9, Mileage = 0)
    elif "private" in mode or "car" in mode or "jeep" in mode:
        st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = row["Ticket_Price_Rate"]
        st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0
        
    # 3. Auto (Ticket = 0, Mileage = KM * Rate)
    elif "auto" in mode or "rickshaw" in mode:
         val = row["Kilometer"] * row["Rate_per_KM"]
         st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = val
         st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = 0.0

    # 4. Public (Ticket = Col 9, Mileage = 0)
    else: 
         st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = row["Ticket_Price_Rate"]
         st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0

# Define Order (1 to 13)
cols_1_to_13 = [
    "Departure_Place", "Departure_Date", "Departure_Time",  # 1, 2, 3
    "Arrival_Place", "Arrival_Date", "Arrival_Time",        # 4, 5, 6
    "Mode_of_Travel",                                       # 7
    "Class_of_Travel",                                      # 8
    "Ticket_Price_Rate",                                    # 9
    "Actual_Ticket_Amount",                                 # 10
    "Kilometer",                                            # 11
    "Rate_per_KM",                                          # 12
    "Mileage_Total"                                         # 13
]

# Ensure cols exist before display (Double Check)
for c in cols_1_to_13:
    if c not in st.session_state['ta_calculation_df'].columns:
        st.session_state['ta_calculation_df'][c] = None

edited_ta = st.data_editor(
    st.session_state['ta_calculation_df'][cols_1_to_13],
    use_container_width=True,
    hide_index=True,
    column_config={
        # Cols 1-7 (From Diary)
        "Departure_Place": st.column_config.TextColumn("1. From", disabled=True),
        "Departure_Date": st.column_config.DateColumn("2. Dep Date", format="DD-MM-YYYY", disabled=True),
        "Departure_Time": st.column_config.TimeColumn("3. Dep Time", format="HH:mm", disabled=True),
        "Arrival_Place": st.column_config.TextColumn("4. To", disabled=True),
        "Arrival_Date": st.column_config.DateColumn("5. Arr Date", format="DD-MM-YYYY", disabled=True),
        "Arrival_Time": st.column_config.TimeColumn("6. Arr Time", format="HH:mm", disabled=True),
        "Mode_of_Travel": st.column_config.TextColumn("7. Mode", disabled=True),
        
        # Cols 8-13 (TA Calculation)
        "Class_of_Travel": st.column_config.TextColumn("8. Class / Vehicle No"),
        
        "Ticket_Price_Rate": st.column_config.NumberColumn(
            "9. Rate/Fare (Rs.)", 
            format="₹ %.2f",
            help="Ticket Price OR Bus Fare Equivalent for Private Car"
        ),
        
        "Actual_Ticket_Amount": st.column_config.NumberColumn(
            "10. Ticket Total", 
            format="₹ %.2f", 
            disabled=True,
            help="Final Amount Claimed for Ticket/Fare"
        ),
        
        "Kilometer": st.column_config.NumberColumn("11. KM", format="%.1f km"),
        "Rate_per_KM": st.column_config.NumberColumn("12. Rate/KM", format="₹ %.2f"),
        
        "Mileage_Total": st.column_config.NumberColumn(
            "13. Mileage Total", 
            format="₹ %.2f", 
            disabled=True,
            help="Calculated as KM * Rate (Col 11 * 12)"
        )
    }
)

st.session_state['ta_calculation_df'].update(edited_ta)
st.session_state['final_ta_data'] = st.session_state['ta_calculation_df']

# --- TOTALS ---
total_ticket = edited_ta["Actual_Ticket_Amount"].sum()
total_mileage = edited_ta["Mileage_Total"].sum()
grand_total = total_ticket + total_mileage

st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("Total Ticket/Fare (Col 10)", f"₹ {total_ticket:,.2f}")
c2.metric("Total Mileage (Col 13)", f"₹ {total_mileage:,.2f}")
c3.metric("💰 Net TA Claim", f"₹ {grand_total:,.2f}")
