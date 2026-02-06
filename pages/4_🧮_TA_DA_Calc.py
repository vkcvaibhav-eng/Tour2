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
# TAB 1: TA Calculation (Smart Fill for KM AND Fare)
# =========================================================
with tab1:
    st.subheader("Transport Allowance (Columns 7 - 13)")
    
    # 1. Initialize Structure
    if 'ta_calculation_df' not in st.session_state:
        # Create a new structure based on the diary
        ta_df = diary_df[["Departure_Place", "Arrival_Place", "Mode_of_Travel"]].copy()
        
        # Add the specific columns (7 to 13)
        # Default Class logic
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

    df = st.session_state['ta_calculation_df']

    # --- BLOCK A: MISSING KILOMETERS (Route-Based) ---
    # Rows that need KM: Auto, Taxi, Rickshaw, Private Car
    needs_km_mask = df["Mode_of_Travel"].str.contains("Auto|Taxi|Rickshaw|Private Car|Car", case=False, na=False)
    missing_km_rows = df[needs_km_mask & (df["Kilometer"] == 0)]

    # --- BLOCK B: MISSING FARES (Row-Based) ---
    # Rows that need Fare (Col 9): Bus, Rail, Air, Private Car (Fare Enquiry)
    # We exclude University/Govt Vehicle (Fare 0) and Auto/Taxi (Mileage based)
    needs_fare_mask = df["Mode_of_Travel"].apply(
        lambda x: any(m in str(x).lower() for m in ["bus", "rail", "train", "flight", "air", "private car", "car"])
        and not any(e in str(x).lower() for e in ["gov", "uni", "auto", "taxi", "rickshaw"])
    )
    missing_fare_rows = df[needs_fare_mask & (df["Ticket_Price_Rate"] == 0)]

    # === DISPLAY WARNINGS & INPUTS ===
    
    if not missing_km_rows.empty or not missing_fare_rows.empty:
        st.warning("⚠️ Some details (Distances or Fares) are missing. Please fill them below to update the table.")
        
        c_fill1, c_fill2 = st.columns(2)
        
        # --- LEFT: Fill Missing Distances ---
        with c_fill1:
            if not missing_km_rows.empty:
                st.info(f"📏 Missing Distances ({len(missing_km_rows)} trips)")
                # Group by Route to ask once
                unique_routes = missing_km_rows[["Departure_Place", "Arrival_Place"]].drop_duplicates()
                
                with st.expander("📝 Add Distances (KM)", expanded=True):
                    for i, route in unique_routes.iterrows():
                        dep = route["Departure_Place"]
                        arr = route["Arrival_Place"]
                        
                        # Check mode for context
                        is_auto = any("Auto" in str(m) for m in missing_km_rows[(missing_km_rows["Departure_Place"]==dep)]["Mode_of_Travel"])
                        
                        col_a, col_b, col_c = st.columns([2, 1, 1])
                        col_a.caption(f"{dep} ⇄ {arr}")
                        
                        km_val = col_b.number_input("KM", min_value=0.0, key=f"km_fix_{i}")
                        
                        # Only ask Rate if it's Auto/Taxi (Private car uses Fare Enquiry)
                        if is_auto:
                            rate_val = col_c.number_input("Rate", value=12.0, key=f"rate_fix_{i}")
                        else:
                            rate_val = 0.0 # Not needed for Car

                        if st.button(f"Apply KM##{i}"):
                            # Apply to ALL matching routes
                            mask = (st.session_state['ta_calculation_df']["Departure_Place"] == dep) & \
                                   (st.session_state['ta_calculation_df']["Arrival_Place"] == arr)
                            st.session_state['ta_calculation_df'].loc[mask, "Kilometer"] = km_val
                            
                            if is_auto:
                                auto_mask = mask & st.session_state['ta_calculation_df']["Mode_of_Travel"].str.contains("Auto|Taxi")
                                st.session_state['ta_calculation_df'].loc[auto_mask, "Rate_per_KM"] = rate_val
                            st.rerun()

        # --- RIGHT: Fill Missing Fares ---
        with c_fill2:
            if not missing_fare_rows.empty:
                st.info(f"💵 Missing Fares ({len(missing_fare_rows)} tickets)")
                with st.expander("📝 Add Ticket/Fare Prices", expanded=True):
                    for idx, row in missing_fare_rows.iterrows():
                        c_f1, c_f2, c_f3 = st.columns([2, 1, 1])
                        c_f1.caption(f"{row['Departure_Place']} ➝ {row['Arrival_Place']} ({row['Mode_of_Travel']})")
                        
                        fare_val = c_f2.number_input("Price (Rs)", min_value=0.0, key=f"fare_fix_{idx}")
                        
                        if c_f3.button("Set Fare", key=f"btn_fare_{idx}"):
                            st.session_state['ta_calculation_df'].at[idx, "Ticket_Price_Rate"] = fare_val
                            st.session_state['ta_calculation_df'].at[idx, "Actual_Ticket_Amount"] = fare_val
                            st.rerun()


    # 3. AUTO-CALCULATION LOGIC (Run every refresh)
    for index, row in st.session_state['ta_calculation_df'].iterrows():
        mode = str(row["Mode_of_Travel"]).lower()
        
        # CASE A: Private Car
        # Logic: User fills Col 9 (Bus Fare) via the "Missing Fare" box.
        # We enforce Col 13 (Mileage) = 0.
        if "private car" in mode:
            # Sync Ticket Total with Rate if user entered it
            st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = row["Ticket_Price_Rate"]
            st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0
            
        # CASE B: University/Govt Vehicle
        elif "vehicle" in mode and "private" not in mode:
             st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = 0.0
             st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0
        
        # CASE C: Auto / Taxi / Rickshaw
        # Logic: Mileage (Col 13) = KM * Rate. Ticket (Col 10) = 0.
        elif "auto" in mode or "taxi" in mode or "rickshaw" in mode:
             val = row["Kilometer"] * row["Rate_per_KM"]
             st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = val
             st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = 0.0

        # CASE D: Bus / Train / Air
        # Logic: Ticket (Col 10) = Col 9. Mileage = 0.
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
                "8. Class / Uni Vehicle No",
                help="Enter Class (II, Sleeper, Economy) or Vehicle Number"
            ),
            
            "Ticket_Price_Rate": st.column_config.NumberColumn(
                "9. Rate/Fare (Rs.)", 
                format="₹ %.2f",
                help="For Private Car, enter Bus Fare here."
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
# TAB 2: DA Calculation
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
