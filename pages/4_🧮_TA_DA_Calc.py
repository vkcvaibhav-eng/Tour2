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
# TAB 1: TA Calculation (Smart Fill for Fares & KM)
# =========================================================
with tab1:
    st.subheader("Transport Allowance (Columns 7 - 13)")
    
    # 1. Initialize Structure
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

    # 2. SMART FILL SYSTEM (KM & FARES)
    df = st.session_state['ta_calculation_df']
    
    # --- Logic to Identify Missing Info ---
    # We ignore "Govt/University Vehicle" completely (they are always 0)
    
    # A. Missing Kilometers (For Auto, Taxi, Private Car)
    needs_km_mask = df["Mode_of_Travel"].str.contains("Auto|Taxi|Rickshaw|Private Car|Car", case=False, na=False)
    missing_km_rows = df[needs_km_mask & (df["Kilometer"] == 0)]
    
    # B. Missing Fares (For Bus, Rail, Air, Private Car)
    # Note: Private Car needs Fare (Col 9) representing "Bus Fare Equivalent"
    needs_fare_mask = df["Mode_of_Travel"].str.contains("Bus|Rail|Air|Flight|Train|Private Car|Car", case=False, na=False)
    missing_fare_rows = df[needs_fare_mask & (df["Ticket_Price_Rate"] == 0)]

    # Combine logical indices to find any row needing attention
    attention_needed = missing_km_rows.index.union(missing_fare_rows.index)
    
    if not attention_needed.empty:
        st.warning(f"⚠️ Found {len(attention_needed)} items needing manual input (Distance or Fare).")
        
        with st.expander("📝 Smart Fill: Add Missing Fares & Distances", expanded=True):
            st.caption("Fill these details once, and I will update the table automatically.")
            
            # Loop through rows that need attention
            # We group by Route + Mode to avoid asking duplicates
            
            # Create a simplified view for grouping
            pending_df = df.loc[attention_needed, ["Departure_Place", "Arrival_Place", "Mode_of_Travel"]].drop_duplicates()
            
            for i, row in pending_df.iterrows():
                dep = row["Departure_Place"]
                arr = row["Arrival_Place"]
                mode = row["Mode_of_Travel"]
                
                # Determine what is missing for this specific Route & Mode
                is_private_car = "Private Car" in mode or "Car" in mode
                is_auto = "Auto" in mode or "Taxi" in mode or "Rickshaw" in mode
                is_public = "Bus" in mode or "Rail" in mode or "Air" in mode or "Train" in mode
                
                # Check current values in the main DF (take the first match)
                current_match = df[
                    (df["Departure_Place"] == dep) & 
                    (df["Arrival_Place"] == arr) & 
                    (df["Mode_of_Travel"] == mode)
                ].iloc[0]
                
                has_km = current_match["Kilometer"] > 0
                has_fare = current_match["Ticket_Price_Rate"] > 0
                
                # UI Layout
                c1, c2, c3, c4 = st.columns([2.5, 1.5, 1.5, 1])
                
                with c1:
                    st.write(f"**{dep}** ➝ **{arr}**")
                    st.caption(f"via {mode}")

                # INPUT 1: DISTANCE (Only if needed & missing)
                km_val = 0.0
                with c2:
                    if (is_private_car or is_auto) and not has_km:
                        km_val = st.number_input(f"Distance (KM)", min_value=0.0, key=f"km_{i}")
                    elif has_km:
                        st.success(f"KM: {current_match['Kilometer']}")
                    else:
                        st.write("---") # Not applicable

                # INPUT 2: FARE / RATE (Only if needed & missing)
                fare_val = 0.0
                rate_km_val = 0.0
                with c3:
                    if is_public and not has_fare:
                        fare_val = st.number_input(f"Ticket Price", min_value=0.0, key=f"fare_{i}")
                    elif is_private_car and not has_fare:
                        fare_val = st.number_input(f"Bus Fare Equiv.", min_value=0.0, key=f"fare_{i}")
                    elif is_auto:
                        # Auto needs Rate per KM, not fixed fare
                        rate_km_val = st.number_input(f"Rate/KM", value=12.0, key=f"rate_{i}")
                    elif has_fare:
                        st.success(f"Fare: {current_match['Ticket_Price_Rate']}")
                    else:
                        st.write("---")

                # UPDATE BUTTON
                with c4:
                    if st.button("Apply", key=f"btn_{i}"):
                        # Find all matching rows
                        mask = (st.session_state['ta_calculation_df']["Departure_Place"] == dep) & \
                               (st.session_state['ta_calculation_df']["Arrival_Place"] == arr) & \
                               (st.session_state['ta_calculation_df']["Mode_of_Travel"] == mode)
                        
                        # Update KM
                        if km_val > 0:
                            st.session_state['ta_calculation_df'].loc[mask, "Kilometer"] = km_val
                        
                        # Update Fare (Col 9)
                        if fare_val > 0:
                            st.session_state['ta_calculation_df'].loc[mask, "Ticket_Price_Rate"] = fare_val
                            
                        # Update Rate/KM (Col 12 - for Auto)
                        if rate_km_val > 0:
                            st.session_state['ta_calculation_df'].loc[mask, "Rate_per_KM"] = rate_km_val
                            
                        st.rerun()

    # 3. AUTO-CALCULATION & GOVT VEHICLE LOGIC
    for index, row in st.session_state['ta_calculation_df'].iterrows():
        mode = str(row["Mode_of_Travel"]).lower()
        
        # --- CASE A: Govt / University Vehicle ---
        # STRICT RULE: NO FARE, NO MILEAGE. Just record.
        if "vehicle" in mode and "private" not in mode:
             st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = 0.0
             st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0
             st.session_state['ta_calculation_df'].at[index, "Ticket_Price_Rate"] = 0.0
        
        # --- CASE B: Private Car ---
        # Logic: Needs KM (Record) and Bus Fare (Col 9). Mileage (Col 13) is 0.
        elif "private car" in mode or "car" in mode:
            # Ticket Total = Bus Fare (Col 9)
            st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = row["Ticket_Price_Rate"]
            # Mileage = 0
            st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0
            
        # --- CASE C: Auto / Taxi / Rickshaw ---
        # Logic: Mileage = KM * Rate. Ticket = 0.
        elif "auto" in mode or "taxi" in mode or "rickshaw" in mode:
             val = row["Kilometer"] * row["Rate_per_KM"]
             st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = val
             st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = 0.0

        # --- CASE D: Public Transport (Bus/Rail/Air) ---
        # Logic: Ticket Total = Fare (Col 9). Mileage = 0.
        else:
             st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = row["Ticket_Price_Rate"]
             st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0

    # 4. The Main Table Editor
    st.markdown("### 📋 Edit Details")
    
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
                help="Edit this to add Vehicle Number"
            ),
            
            "Ticket_Price_Rate": st.column_config.NumberColumn(
                "9. Rate/Fare (Rs.)", 
                format="₹ %.2f",
                help="For Private Car, enter Bus Fare here."
            ),
            "Actual_Ticket_Amount": st.column_config.NumberColumn(
                "10. Total Ticket", 
                format="₹ %.2f",
                disabled=True
            ),
            
            "Kilometer": st.column_config.NumberColumn("11. KM", format="%.1f km"),
            "Rate_per_KM": st.column_config.NumberColumn("12. Rate/KM", format="₹ %.2f"),
            
            "Mileage_Total": st.column_config.NumberColumn(
                "13. Total (Mileage)", 
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
