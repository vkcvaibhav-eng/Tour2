import streamlit as st
import pandas as pd

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
# INITIALIZE STRUCTURE
# =========================================================
if 'ta_calculation_df' not in st.session_state:
    # Create a new structure based on the diary
    ta_df = diary_df[["Departure_Place", "Arrival_Place", "Mode_of_Travel"]].copy()
    
    # Set Default Class / Vehicle No
    ta_df["Class_of_Travel"] = ta_df.apply(
        lambda x: "Govt. Vehicle" if "Vehicle" in str(x["Mode_of_Travel"]) and "Private" not in str(x["Mode_of_Travel"]) else "Ordinary", 
        axis=1
    )
    
    ta_df["Ticket_Price_Rate"] = 0.0      # Col 9 (Fare or Rate)
    ta_df["Actual_Ticket_Amount"] = 0.0   # Col 10 (Total Ticket)
    ta_df["Kilometer"] = 0.0              # Col 11
    ta_df["Rate_per_KM"] = 0.0            # Col 12 (Only for Auto/Taxi)
    ta_df["Mileage_Total"] = 0.0          # Col 13 (Calculated)
    
    st.session_state['ta_calculation_df'] = ta_df

# =========================================================
# SMART FILL SYSTEM (KM & FARES)
# =========================================================
df = st.session_state['ta_calculation_df']

# Identify rows needing input (excluding Govt Vehicles)
needs_km_mask = df["Mode_of_Travel"].str.contains("Auto|Taxi|Rickshaw|Private Car|Car", case=False, na=False)
missing_km_rows = df[needs_km_mask & (df["Kilometer"] == 0)]

needs_fare_mask = df["Mode_of_Travel"].str.contains("Bus|Rail|Air|Flight|Train|Private Car|Car", case=False, na=False)
missing_fare_rows = df[needs_fare_mask & (df["Ticket_Price_Rate"] == 0)]

attention_needed = missing_km_rows.index.union(missing_fare_rows.index)

if not attention_needed.empty:
    st.warning(f"⚠️ Found {len(attention_needed)} items needing manual input (Distance or Fare).")
    
    with st.expander("📝 Smart Fill: Add Missing Fares & Distances", expanded=True):
        st.caption("Fill these details once, and I will update the table automatically.")
        
        # Group by Route + Mode
        pending_df = df.loc[attention_needed, ["Departure_Place", "Arrival_Place", "Mode_of_Travel"]].drop_duplicates()
        
        for i, row in pending_df.iterrows():
            dep = row["Departure_Place"]
            arr = row["Arrival_Place"]
            mode = row["Mode_of_Travel"]
            
            current_match = df[
                (df["Departure_Place"] == dep) & 
                (df["Arrival_Place"] == arr) & 
                (df["Mode_of_Travel"] == mode)
            ].iloc[0]
            
            has_km = current_match["Kilometer"] > 0
            has_fare = current_match["Ticket_Price_Rate"] > 0
            
            is_private_car = "Private Car" in mode or "Car" in mode
            is_auto = "Auto" in mode or "Taxi" in mode or "Rickshaw" in mode
            is_public = "Bus" in mode or "Rail" in mode or "Air" in mode or "Train" in mode

            c1, c2, c3, c4 = st.columns([2.5, 1.5, 1.5, 1])
            with c1:
                st.write(f"**{dep}** ➝ **{arr}**")
                st.caption(f"via {mode}")

            # INPUT 1: DISTANCE
            km_val = 0.0
            with c2:
                if (is_private_car or is_auto) and not has_km:
                    km_val = st.number_input(f"Distance (KM)", min_value=0.0, key=f"km_{i}")
                elif has_km:
                    st.success(f"KM: {current_match['Kilometer']}")
                else:
                    st.write("---")

            # INPUT 2: FARE / RATE
            fare_val = 0.0
            rate_km_val = 0.0
            with c3:
                if is_public and not has_fare:
                    fare_val = st.number_input(f"Ticket Price", min_value=0.0, key=f"fare_{i}")
                elif is_private_car and not has_fare:
                    fare_val = st.number_input(f"Bus Fare Equiv.", min_value=0.0, key=f"fare_{i}")
                elif is_auto:
                    rate_km_val = st.number_input(f"Rate/KM", value=12.0, key=f"rate_{i}")
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
    
    if "vehicle" in mode and "private" not in mode: # Govt Vehicle
         st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = 0.0
         st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0
         st.session_state['ta_calculation_df'].at[index, "Ticket_Price_Rate"] = 0.0
    
    elif "private car" in mode or "car" in mode:
        st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = row["Ticket_Price_Rate"]
        st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0
        
    elif "auto" in mode or "taxi" in mode or "rickshaw" in mode:
         val = row["Kilometer"] * row["Rate_per_KM"]
         st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = val
         st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = 0.0

    else: # Public Transport
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
        "Ticket_Price_Rate": st.column_config.NumberColumn("9. Rate/Fare (Rs.)", format="₹ %.2f"),
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
