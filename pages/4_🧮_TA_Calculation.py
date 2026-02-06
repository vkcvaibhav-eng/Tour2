import streamlit as st
import pandas as pd
import json

st.set_page_config(layout="wide")
st.title("🧮 TA Calculation (Transport Allowance)")

# Check if Page 3 was completed
if 'final_tour_diary' not in st.session_state:
    st.error("Please finish 'Page 3: Tour Diary' first.")
    st.stop()

# Get the clean diary from Page 3
diary_df = st.session_state['final_tour_diary']

st.info("Step 1: Calculate your Transport Allowance (Tickets, Private Car, Auto/Taxi).")

# =========================================================
# HELPER: RETRIEVE KM FROM ORIGINAL RAW DATA
# =========================================================
def try_get_km_from_raw(dep_date, dep_place):
    """
    Looks back at the raw Gemini JSON to find 'KM' or 'Distance' 
    if it was lost during the Page 3 editing process.
    """
    raw_data = st.session_state.get('extracted_data', {})
    
    # 1. Parse JSON if it's a string
    if isinstance(raw_data, str):
        try:
            if "```json" in raw_data:
                raw_data = json.loads(raw_data.split("```json")[1].split("```")[0])
            elif "```" in raw_data:
                raw_data = json.loads(raw_data.split("```")[1].split("```")[0])
            else:
                raw_data = json.loads(raw_data)
        except:
            return 0.0

    # 2. Search for the row in the raw list
    if isinstance(raw_data, dict):
        tour_list = raw_data.get("tour_diary", [])
        for item in tour_list:
            # Simple match attempt
            raw_place = str(item.get("Departure_Place", "")).strip().lower()
            target_place = str(dep_place).strip().lower()
            
            # If dates match (loosely) and place matches
            if raw_place in target_place or target_place in raw_place:
                # Try to extract KM
                val = item.get("KM") or item.get("Distance") or item.get("Kilometer")
                if val:
                    try:
                        return float(str(val).replace("km", "").strip())
                    except:
                        pass
    return 0.0

# =========================================================
# INITIALIZE STRUCTURE & EXTRACT KM
# =========================================================
if 'ta_calculation_df' not in st.session_state:
    # Create a new structure based on the diary
    ta_df = diary_df[["Departure_Place", "Arrival_Place", "Mode_of_Travel", "Departure_Date"]].copy()
    
    # --- 1. SET CLASS / VEHICLE NO ---
    ta_df["Class_of_Travel"] = ta_df.apply(
        lambda x: "Govt. Vehicle" if "University" in str(x["Mode_of_Travel"]) or "Govt" in str(x["Mode_of_Travel"]) else "Ordinary", 
        axis=1
    )
    
    # --- 2. INITIALIZE COLUMNS ---
    ta_df["Ticket_Price_Rate"] = 0.0      # Col 9 (Fare or Bus Fare Equiv)
    ta_df["Actual_Ticket_Amount"] = 0.0   # Col 10 (Total Ticket)
    ta_df["Kilometer"] = 0.0              # Col 11 (Distance)
    ta_df["Rate_per_KM"] = 0.0            # Col 12 (Only for Auto)
    ta_df["Mileage_Total"] = 0.0          # Col 13 (Calculated)

    # --- 3. INTELLIGENT KM EXTRACTION ---
    for idx, row in ta_df.iterrows():
        mode = str(row["Mode_of_Travel"]).lower()
        
        # Only extract KM for Private/Uni vehicles (as per rule)
        if "private" in mode or "university" in mode or "car" in mode or "jeep" in mode:
            # First, check if 'KM' exists in the diary dataframe itself (Page 3)
            if "KM" in diary_df.columns and pd.notnull(diary_df.loc[idx, "KM"]):
                try:
                    ta_df.at[idx, "Kilometer"] = float(diary_df.loc[idx, "KM"])
                except:
                    pass
            
            # If still 0, look back at Raw Gemini Data (Page 2 Extraction)
            if ta_df.at[idx, "Kilometer"] == 0:
                extracted_km = try_get_km_from_raw(row["Departure_Date"], row["Departure_Place"])
                ta_df.at[idx, "Kilometer"] = extracted_km

    st.session_state['ta_calculation_df'] = ta_df

# =========================================================
# SMART FILL SYSTEM (LOGIC UPDATE)
# =========================================================
df = st.session_state['ta_calculation_df']

# --- Identify Missing Information ---

# A. Private Car: Needs 'Fare' (Bus Equivalent) if 0. (KM should have been extracted)
pvt_mask = df["Mode_of_Travel"].str.contains("Private|Car|Jeep", case=False, na=False)
missing_pvt_fare = df[pvt_mask & (df["Ticket_Price_Rate"] == 0)]
missing_pvt_km = df[pvt_mask & (df["Kilometer"] == 0)] # Fallback if extraction failed

# B. Auto Rickshaw: Needs 'KM' (Column 11) and 'Rate' (Column 12)
auto_mask = df["Mode_of_Travel"].str.contains("Auto|Rickshaw", case=False, na=False)
missing_auto_data = df[auto_mask & ((df["Kilometer"] == 0) | (df["Rate_per_KM"] == 0))]

# C. Public Transport: Needs 'Fare' (Column 9)
pub_mask = df["Mode_of_Travel"].str.contains("Bus|Rail|Train|Flight|Air|Taxi", case=False, na=False)
missing_pub_fare = df[pub_mask & (df["Ticket_Price_Rate"] == 0)]

# Combine all rows needing attention
attention_needed = missing_pvt_fare.index.union(missing_pvt_km.index).union(missing_auto_data.index).union(missing_pub_fare.index)

if not attention_needed.empty:
    st.warning(f"⚠️ Found {len(attention_needed)} items needing manual input (Fares or Missing Distances).")
    
    with st.expander("📝 Smart Fill: Add Missing Fares & Distances", expanded=True):
        st.caption("Fill these details once, and I will update the table automatically.")
        
        # Group by Route + Mode to avoid duplicates
        pending_df = df.loc[attention_needed, ["Departure_Place", "Arrival_Place", "Mode_of_Travel"]].drop_duplicates()
        
        for i, row in pending_df.iterrows():
            dep = row["Departure_Place"]
            arr = row["Arrival_Place"]
            mode = str(row["Mode_of_Travel"])
            
            # Get current values to see what's missing
            current_match = df[
                (df["Departure_Place"] == dep) & 
                (df["Arrival_Place"] == arr) & 
                (df["Mode_of_Travel"] == mode)
            ].iloc[0]
            
            has_km = current_match["Kilometer"] > 0
            has_fare = current_match["Ticket_Price_Rate"] > 0
            has_rate_km = current_match["Rate_per_KM"] > 0
            
            # Flag Types
            is_private = "Private" in mode or "Car" in mode
            is_auto = "Auto" in mode or "Rickshaw" in mode
            is_public = not (is_private or is_auto) and "University" not in mode

            c1, c2, c3, c4 = st.columns([2.5, 1.5, 1.5, 1])
            with c1:
                st.write(f"**{dep}** ➝ **{arr}**")
                st.caption(f"via {mode}")

            # INPUT 1: DISTANCE (Col 11)
            km_val = 0.0
            with c2:
                # Private/Uni: Should have been extracted. If 0, ask.
                # Auto: Always ask.
                if (is_private or is_auto) and not has_km:
                    km_val = st.number_input(f"Distance (KM)", min_value=0.0, key=f"km_{i}")
                elif has_km:
                    st.success(f"KM: {current_match['Kilometer']}")
                else:
                    st.write("---")

            # INPUT 2: RATE / FARE (Col 9 or 12)
            fare_val = 0.0
            rate_km_val = 0.0
            with c3:
                # Private Car: Ask for Bus Fare Equivalent (Col 9) if Fare Enquiry missing
                if is_private and not has_fare:
                    fare_val = st.number_input(f"Bus Fare Equiv.", min_value=0.0, key=f"fare_{i}")
                
                # Auto: Ask for Rate per KM (Col 12)
                elif is_auto and not has_rate_km:
                    rate_km_val = st.number_input(f"Rate/KM", value=12.0, key=f"rate_{i}")
                
                # Public: Ask for Ticket Price (Col 9)
                elif is_public and not has_fare:
                    fare_val = st.number_input(f"Ticket Price", min_value=0.0, key=f"fare_{i}")
                
                elif has_fare:
                    st.success(f"Fare: {current_match['Ticket_Price_Rate']}")
                else:
                    st.write("---")

            with c4:
                if st.button("Apply", key=f"btn_{i}"):
                    mask = (st.session_state['ta_calculation_df']["Departure_Place"] == dep) & \
                           (st.session_state['ta_calculation_df']["Arrival_Place"] == arr) & \
                           (st.session_state['ta_calculation_df']["Mode_of_Travel"] == mode)
                    
                    if km_val > 0: st.session_state['ta_calculation_df'].loc[mask, "Kilometer"] = km_val
                    if fare_val > 0: st.session_state['ta_calculation_df'].loc[mask, "Ticket_Price_Rate"] = fare_val
                    if rate_km_val > 0: st.session_state['ta_calculation_df'].loc[mask, "Rate_per_KM"] = rate_km_val
                    st.rerun()

# =========================================================
# AUTO CALCULATION LOGIC
# =========================================================
for index, row in st.session_state['ta_calculation_df'].iterrows():
    mode = str(row["Mode_of_Travel"]).lower()
    
    # 1. UNIVERSITY / GOVT VEHICLE
    if "university" in mode or ("govt" in mode and "private" not in mode):
         # KM is extracted for record, but Money is 0
         st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = 0.0
         st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0
         st.session_state['ta_calculation_df'].at[index, "Ticket_Price_Rate"] = 0.0
    
    # 2. PRIVATE VEHICLE (Car/Jeep)
    elif "private" in mode or "car" in mode or "jeep" in mode:
        # Col 10 (Total) = Col 9 (Bus Fare Equivalent)
        # Note: Even though we have KM (Col 11), we DO NOT multiply by Rate/KM.
        # We assume Private Vehicle claim is restricted to Bus Fare (Fare Enquiry).
        st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = row["Ticket_Price_Rate"]
        st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0
        
    # 3. AUTO RICKSHAW
    elif "auto" in mode or "rickshaw" in mode:
         # Col 13 (Mileage) = KM * Rate
         val = row["Kilometer"] * row["Rate_per_KM"]
         st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = val
         st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = 0.0

    # 4. PUBLIC TRANSPORT (Bus, Rail, Flight, Taxi)
    else: 
         # Col 10 = Col 9 (Ticket Price)
         st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = row["Ticket_Price_Rate"]
         st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0

# =========================================================
# MAIN TABLE
# =========================================================
st.markdown("### 📋 Review Transport Allowance")
edited_ta = st.data_editor(
    st.session_state['ta_calculation_df'],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Departure_Place": st.column_config.TextColumn("From", disabled=True),
        "Arrival_Place": st.column_config.TextColumn("To", disabled=True),
        "Mode_of_Travel": st.column_config.TextColumn("7. Mode", disabled=True),
        "Class_of_Travel": st.column_config.TextColumn("8. Class / Vehicle No"),
        
        "Ticket_Price_Rate": st.column_config.NumberColumn(
            "9. Rate/Fare (Rs.)", 
            format="₹ %.2f",
            help="For Private Car, this is the Bus Fare Equivalent."
        ),
        
        "Actual_Ticket_Amount": st.column_config.NumberColumn("10. Total Ticket", format="₹ %.2f", disabled=True),
        "Kilometer": st.column_config.NumberColumn("11. KM", format="%.1f km"),
        "Rate_per_KM": st.column_config.NumberColumn("12. Rate/KM", format="₹ %.2f"),
        "Mileage_Total": st.column_config.NumberColumn("13. Total (Mileage)", format="₹ %.2f", disabled=True)
    }
)

st.session_state['ta_calculation_df'] = edited_ta

# =========================================================
# TOTALS & NAVIGATION
# =========================================================
total_ticket = edited_ta["Actual_Ticket_Amount"].sum()
total_mileage = edited_ta["Mileage_Total"].sum()
grand_total = total_ticket + total_mileage

st.divider()
c_tot1, c_tot2, c_tot3 = st.columns(3)
c_tot1.metric("Ticket Total (Col 10)", f"₹ {total_ticket:,.2f}")
c_tot2.metric("Mileage Total (Col 13)", f"₹ {total_mileage:,.2f}")
c_tot3.metric("💰 Net TA Claim", f"₹ {grand_total:,.2f}")

st.markdown("---")
if st.button("💾 Save & Go to DA Calculation (Page 5)"):
    st.session_state['final_ta_data'] = st.session_state['ta_calculation_df']
    st.switch_page("pages/5_📅_DA_Calculation.py")
