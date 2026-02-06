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

# Create Tabs
tab1, tab2 = st.tabs(["🚆 TA Calculation (Tickets & Fuel)", "📅 DA Calculation (Allowance)"])

# =========================================================
# TAB 1: TA Calculation (Updated Logic)
# =========================================================
with tab1:
    st.subheader("Transport Allowance (Columns 7 - 13)")
    
    # --- 1. Initialize Main Dataframe ---
    if 'ta_calculation_df' not in st.session_state:
        ta_df = diary_df[["Departure_Place", "Arrival_Place", "Mode_of_Travel"]].copy()
        
        # Add Columns 7-13
        ta_df["Class_of_Travel"] = "Ordinary" # Col 8
        ta_df["Ticket_Price_Rate"] = 0.0      # Col 9 (Rate/Fare)
        ta_df["Actual_Ticket_Amount"] = 0.0   # Col 10 (Total Fare)
        ta_df["Kilometer"] = 0.0              # Col 11
        ta_df["Rate_per_KM"] = 0.0            # Col 12
        ta_df["Mileage_Total"] = 0.0          # Col 13 (Calculated)
        
        # Set Default Rate for Auto/Taxi (e.g., 12 Rs)
        # We don't set it for Private Car because that uses Fare Enquiry
        mask_road = ta_df["Mode_of_Travel"].str.contains("Auto|Rickshaw|Taxi", case=False, na=False)
        ta_df.loc[mask_road, "Rate_per_KM"] = 12.0 
        
        st.session_state['ta_calculation_df'] = ta_df

    df = st.session_state['ta_calculation_df']

    # --- 2. SMART ROUTE MANAGER (Fix for Duplicate Questions) ---
    # Filter for modes that need Kilometers (Auto, Rickshaw, Taxi)
    # Private Car is excluded here because it uses Fare Enquiry (Col 9) as per your note.
    road_modes = ["Auto", "Rickshaw", "Taxi"]
    road_mask = df["Mode_of_Travel"].str.contains("|".join(road_modes), case=False, na=False)
    
    if road_mask.any():
        st.info("📍 **Route Distance Manager** (Enter distance once, applies to all same trips)")
        
        # Identify Unique Routes (Departure <-> Arrival)
        unique_routes = df[road_mask][["Departure_Place", "Arrival_Place"]].drop_duplicates()
        
        # We use a temporary editor to let user input KM for unique routes
        if 'route_master_df' not in st.session_state:
            unique_routes["Distance_KM"] = 0.0
            st.session_state['route_master_df'] = unique_routes
        
        # Show mini table for routes
        edited_routes = st.data_editor(
            st.session_state['route_master_df'],
            hide_index=True,
            column_config={
                "Departure_Place": st.column_config.TextColumn("From", disabled=True),
                "Arrival_Place": st.column_config.TextColumn("To", disabled=True),
                "Distance_KM": st.column_config.NumberColumn("Kilometers", format="%.1f km")
            },
            key="route_editor"
        )
        st.session_state['route_master_df'] = edited_routes
        
        # Apply these KMs back to the Main Dataframe
        if st.button("🔄 Apply Distances to Main Table"):
            for index, row in edited_routes.iterrows():
                # Match From/To and update KM
                mask = (
                    (st.session_state['ta_calculation_df']["Departure_Place"] == row['Departure_Place']) &
                    (st.session_state['ta_calculation_df']["Arrival_Place"] == row['Arrival_Place']) &
                    (st.session_state['ta_calculation_df']["Mode_of_Travel"].str.contains("|".join(road_modes), case=False, na=False))
                )
                st.session_state['ta_calculation_df'].loc[mask, "Kilometer"] = row['Distance_KM']
            st.success("Distances updated!")
            st.rerun()
            
    st.markdown("---")

    # --- 3. PRIVATE CAR & FARE ENQUIRY NOTICE ---
    # Check if Private Car exists
    pvt_car_mask = st.session_state['ta_calculation_df']["Mode_of_Travel"].str.contains("Private|Car", case=False, na=False)
    if pvt_car_mask.any():
        st.warning(
            "🚗 **Private Vehicle Detected:** "
            "Since private vehicle claims are not allowed, please enter the **Admissible Fare (Bus/Rail)** "
            "based on your Fare Enquiry in **Column 9** below."
        )

    # --- 4. CALCULATION LOGIC ---
    # A. For Auto/Taxi: Col 13 = KM * Rate
    st.session_state['ta_calculation_df'].loc[road_mask, "Mileage_Total"] = (
        st.session_state['ta_calculation_df'].loc[road_mask, "Kilometer"] * st.session_state['ta_calculation_df'].loc[road_mask, "Rate_per_KM"]
    )
    
    # B. For Private Car/Bus/Rail: Col 10 = Col 9 (Rate is the Ticket Amount)
    # We assume Ticket Price (Col 9) is the Total if manually entered
    non_mileage_mask = ~road_mask
    st.session_state['ta_calculation_df'].loc[non_mileage_mask, "Actual_Ticket_Amount"] = (
        st.session_state['ta_calculation_df'].loc[non_mileage_mask, "Ticket_Price_Rate"]
    )
    # Ensure Private Car has 0 Mileage Total (since it uses Fare/Ticket logic)
    st.session_state['ta_calculation_df'].loc[non_mileage_mask, "Mileage_Total"] = 0.0


    # --- 5. MAIN EDITOR ---
    edited_ta = st.data_editor(
        st.session_state['ta_calculation_df'],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Departure_Place": st.column_config.TextColumn("From", disabled=True),
            "Arrival_Place": st.column_config.TextColumn("To", disabled=True),
            "Mode_of_Travel": st.column_config.TextColumn("7. Mode", disabled=True),
            
            "Class_of_Travel": st.column_config.SelectboxColumn(
                "8. Class",
                options=[
                    "II/III (Rail)", "First Class (Rail)", "CC (Rail)", 
                    "Economy (Air)", "Business (Air)", 
                    "Express (Bus)", "Super Express (Bus)", "Luxury (Bus)",
                    "Ordinary", "N/A"
                ],
                width="medium"
            ),
            
            "Ticket_Price_Rate": st.column_config.NumberColumn(
                "9. Ticket/Fare Rate (Rs.)", 
                format="₹ %.2f",
                help="For Private Car, enter Fare Enquiry rate here."
            ),
            "Actual_Ticket_Amount": st.column_config.NumberColumn(
                "10. Ticket Total (Rs.)", 
                format="₹ %.2f",
                disabled=True, # Auto-filled from Col 9 for non-mileage
                help="Auto-calculated from Col 9"
            ),
            
            "Kilometer": st.column_config.NumberColumn("11. KM", format="%.1f km"),
            "Rate_per_KM": st.column_config.NumberColumn("12. Rate/KM (Rs.)", format="₹ %.2f"),
            
            "Mileage_Total": st.column_config.NumberColumn(
                "13. Total (KM*Rate)", 
                format="₹ %.2f", 
                disabled=True, 
                help="Auto-calculated: Col 11 * Col 12 (For Auto/Taxi only)"
            )
        }
    )

    # Sync State
    st.session_state['ta_calculation_df'] = edited_ta
    
    # --- 6. TOTALS ---
    total_ticket = edited_ta["Actual_Ticket_Amount"].sum()
    total_mileage = edited_ta["Mileage_Total"].sum()
    grand_total = total_ticket + total_mileage
    
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Ticket/Fare Total (Col 10)", f"₹ {total_ticket:,.2f}")
    c2.metric("Mileage Total (Col 13)", f"₹ {total_mileage:,.2f}")
    c3.metric("💰 Net TA Claim", f"₹ {grand_total:,.2f}")


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
