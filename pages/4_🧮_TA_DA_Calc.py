import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("🧮 TA & DA Calculation")

# Check if Page 3 was completed
if 'final_tour_diary' not in st.session_state:
    st.error("Please finish 'Page 3: Tour Diary' first.")
    st.stop()

# Get the clean diary from Page 3
diary_df = st.session_state['final_tour_diary']

# Create Tabs for TA (Tickets) and DA (Daily Allowance)
tab1, tab2 = st.tabs(["🚆 TA Calculation (Tickets & Fuel)", "📅 DA Calculation (Allowance)"])

# =========================================================
# TAB 1: TA Calculation (Optimized for Private Car & Duplicates)
# =========================================================
with tab1:
    st.subheader("Transport Allowance (Columns 7 - 13)")
    
    # 1. Initialize Structure
    if 'ta_calculation_df' not in st.session_state:
        # Create a new structure based on the diary
        ta_df = diary_df[["Departure_Place", "Arrival_Place", "Mode_of_Travel"]].copy()
        
        # Add the specific columns (7 to 13)
        # Default Class is "Ordinary" unless it's a University Vehicle
        ta_df["Class_of_Travel"] = ta_df.apply(
            lambda x: "Govt. Vehicle No: " if "Vehicle" in str(x["Mode_of_Travel"]) else "Ordinary", 
            axis=1
        )
        
        ta_df["Ticket_Price_Rate"] = 0.0      # Col 9 (Fare or Rate)
        ta_df["Actual_Ticket_Amount"] = 0.0   # Col 10 (Total Ticket)
        ta_df["Kilometer"] = 0.0              # Col 11
        ta_df["Rate_per_KM"] = 0.0            # Col 12 (Only for Auto/Taxi)
        ta_df["Mileage_Total"] = 0.0          # Col 13 (Calculated)
        
        st.session_state['ta_calculation_df'] = ta_df

    # 2. SMART LOGIC: Group Duplicate Routes & Handle Private Car
    df = st.session_state['ta_calculation_df']
    
    # Filter rows that usually need Kilometers (Auto, Taxi, Private Car) but currently have 0 KM
    # We exclude University Vehicles from mandatory KM ask since TA is 0 anyway (unless you want it for record)
    needs_km_mask = df["Mode_of_Travel"].str.contains("Auto|Taxi|Rickshaw|Private Car|Car", case=False, na=False)
    missing_km_rows = df[needs_km_mask & (df["Kilometer"] == 0)]

    if not missing_km_rows.empty:
        # Group by Route (From -> To) to avoid asking the same distance multiple times
        unique_missing_routes = missing_km_rows[["Departure_Place", "Arrival_Place"]].drop_duplicates()
        
        st.warning(f"⚠️ Found {len(missing_km_rows)} trips with missing Kilometers. Please fill them once below.")
        
        with st.expander("📝 Add Missing Distances (Auto-applies to all matching trips)", expanded=True):
            
            # Loop through UNIQUE routes only
            for i, route in unique_missing_routes.iterrows():
                dep = route["Departure_Place"]
                arr = route["Arrival_Place"]
                
                # Check what kind of travel happens on this route to decide what to ask
                modes_on_route = df[
                    (df["Departure_Place"] == dep) & 
                    (df["Arrival_Place"] == arr)
                ]["Mode_of_Travel"].unique()
                
                is_private_car = any("Private Car" in m for m in modes_on_route)
                is_auto_taxi = any("Auto" in m or "Taxi" in m or "Rickshaw" in m for m in modes_on_route)
                
                c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 1])
                
                with c1:
                    st.write(f"**{dep}** ⇄ **{arr}**")
                    if is_private_car:
                        st.caption("🚗 Private Car detected (Bus Fare applies)")
                    if is_auto_taxi:
                        st.caption("🛺 Auto/Taxi detected (Mileage applies)")

                # Input for KM (Applies to both Private Car & Auto)
                with c2:
                    km_input = st.number_input(f"Distance (KM)", min_value=0.0, key=f"km_{i}")

                # Input for Rate (Only if Auto/Taxi involved)
                # If it's ONLY Private Car, we don't need Rate/KM because we use Bus Fare (Col 9)
                rate_input = 0.0
                with c3:
                    if is_auto_taxi:
                        rate_input = st.number_input(f"Rate/KM (Auto Only)", value=12.0, key=f"rate_{i}")
                    else:
                        st.write("---") # No rate needed for Private Car mileage

                with c4:
                    if st.button("Apply", key=f"btn_{i}"):
                        # Update ALL rows matching this route
                        mask = (st.session_state['ta_calculation_df']["Departure_Place"] == dep) & \
                               (st.session_state['ta_calculation_df']["Arrival_Place"] == arr)
                        
                        st.session_state['ta_calculation_df'].loc[mask, "Kilometer"] = km_input
                        
                        # Only apply Rate/KM to Auto/Taxi rows, NOT Private Car rows
                        if is_auto_taxi:
                            auto_mask = mask & st.session_state['ta_calculation_df']["Mode_of_Travel"].str.contains("Auto|Taxi|Rickshaw", case=False)
                            st.session_state['ta_calculation_df'].loc[auto_mask, "Rate_per_KM"] = rate_input
                        
                        st.rerun()

    # 3. AUTO-CALCULATION LOGIC
    # We define specific logic per row
    for index, row in st.session_state['ta_calculation_df'].iterrows():
        mode = str(row["Mode_of_Travel"]).lower()
        
        # CASE A: Private Car
        # Logic: User fills Col 9 (Bus Fare). Col 10 = Col 9. Col 13 (Mileage) = 0.
        if "private car" in mode:
            # Sync Ticket Total with Rate if user entered it
            st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = row["Ticket_Price_Rate"]
            # Ensure Mileage Total is 0 (we don't pay mileage for private car, we pay bus fare)
            st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0
            
        # CASE B: University Vehicle
        # Logic: All Money Columns = 0.
        elif "vehicle" in mode and "private" not in mode: # Matches 'Govt Vehicle', 'University Vehicle'
             st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = 0.0
             st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0
        
        # CASE C: Auto / Taxi / Rickshaw
        # Logic: Col 13 = KM * Rate. Col 9/10 = 0.
        elif "auto" in mode or "taxi" in mode or "rickshaw" in mode:
             # Calculate Mileage
             val = row["Kilometer"] * row["Rate_per_KM"]
             st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = val
             # Clear Ticket amounts to avoid double counting
             st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = 0.0

        # CASE D: Regular Bus / Train / Air
        # Logic: Col 10 = Col 9 * (Number of tickets? usually 1). Col 13 = 0.
        else:
             # Just sync Col 10 with Col 9
             st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = row["Ticket_Price_Rate"]
             st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0

    # 4. The Main Table Editor
    st.markdown("### 📋 Edit Details")
    st.caption("For **Private Car**, enter the equivalent Bus Fare in 'Rate (Col 9)'. The Mileage (Col 13) will remain 0, but KM (Col 11) is saved.")
    
    edited_ta = st.data_editor(
        st.session_state['ta_calculation_df'],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Departure_Place": st.column_config.TextColumn("From", disabled=True),
            "Arrival_Place": st.column_config.TextColumn("To", disabled=True),
            "Mode_of_Travel": st.column_config.TextColumn("7. Mode", disabled=True),
            
            "Class_of_Travel": st.column_config.TextColumn(
                "8. Class / Vehicle No",
                help="For Uni Vehicle, write Number here."
            ),
            
            "Ticket_Price_Rate": st.column_config.NumberColumn(
                "9. Rate/Fare (Rs.)", 
                format="₹ %.2f",
                help="Enter Bus Fare here for Private Car"
            ),
            "Actual_Ticket_Amount": st.column_config.NumberColumn(
                "10. Total Ticket (Rs.)", 
                format="₹ %.2f",
                disabled=True
            ),
            
            "Kilometer": st.column_config.NumberColumn("11. KM", format="%.1f km"),
            "Rate_per_KM": st.column_config.NumberColumn("12. Rate/KM (Auto)", format="₹ %.2f"),
            
            "Mileage_Total": st.column_config.NumberColumn(
                "13. Total (KM*Rate)", 
                format="₹ %.2f", 
                disabled=True
            )
        }
    )

    # Update state
    st.session_state['ta_calculation_df'] = edited_ta
    
    # 5. Final Totals
    total_ticket = edited_ta["Actual_Ticket_Amount"].sum()
    total_mileage = edited_ta["Mileage_Total"].sum()
    grand_total = total_ticket + total_mileage
    
    st.divider()
    c_tot1, c_tot2, c_tot3 = st.columns(3)
    c_tot1.metric("Ticket Total (Col 10)", f"₹ {total_ticket:,.2f}")
    c_tot2.metric("Mileage Total (Col 13)", f"₹ {total_mileage:,.2f}")
    c_tot3.metric("💰 Net TA Claim", f"₹ {grand_total:,.2f}")


# =========================================================
# TAB 2: DA Calculation (Standard)
# =========================================================
with tab2:
    st.subheader("Daily Allowance (DA)")
    st.caption("The system will calculate duration based on your verified dates/times.")

    if st.button("🔄 Recalculate DA based on Diary"):
        da_data = []
        for index, row in diary_df.iterrows():
            da_data.append({
                "Date": row['Arrival_Date'], 
                "Stay_At": row['Arrival_Place'],
                "Duration_Hours": 0, 
                "Pay_Level_Rate": 0, 
                "DA_Claimed": 0
            })
        st.session_state['da_calculation_df'] = pd.DataFrame(da_data)
        st.rerun()

    if 'da_calculation_df' in st.session_state:
        st.session_state['da_calculation_df'] = st.data_editor(
            st.session_state['da_calculation_df'],
            use_container_width=True,
            num_rows="dynamic"
        )
        
        total_da = st.session_state['da_calculation_df']["DA_Claimed"].sum()
        st.metric("Total DA Claim", f"₹ {total_da:,.2f}")

st.markdown("---")
if st.button("💾 Save Final Calculations"):
    st.session_state['final_ta_data'] = st.session_state['ta_calculation_df']
    st.session_state['final_da_data'] = st.session_state.get('da_calculation_df', pd.DataFrame())
    st.success("Calculations Saved! Ready for Export on Page 5.")
