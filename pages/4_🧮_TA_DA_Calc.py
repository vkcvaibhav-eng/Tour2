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
# TAB 1: TA Calculation (Updated to 7-13 Format)
# =========================================================
with tab1:
    st.subheader("Transport Allowance (Columns 7 - 13)")
    
    # 1. Initialize Structure with Exact Columns Requested
    if 'ta_calculation_df' not in st.session_state:
        # Create a new structure based on the diary
        ta_df = diary_df[["Departure_Place", "Arrival_Place", "Mode_of_Travel"]].copy()
        
        # Add the specific columns (7 to 13)
        ta_df["Class_of_Travel"] = "Ordinary" # Col 8
        ta_df["Ticket_Price_Rate"] = 0.0      # Col 9
        ta_df["Actual_Ticket_Amount"] = 0.0   # Col 10
        ta_df["Kilometer"] = 0.0              # Col 11
        ta_df["Rate_per_KM"] = 0.0            # Col 12
        ta_df["Mileage_Total"] = 0.0          # Col 13 (Calculated)
        
        st.session_state['ta_calculation_df'] = ta_df

    # 2. Logic: Smart Fill for Missing Kilometers (The "Ask Separately" Feature)
    df = st.session_state['ta_calculation_df']
    
    # Identify rows that likely need Kilometers (Auto, Taxi, Car) but have 0 KM
    road_travel_mask = df["Mode_of_Travel"].str.contains("Auto|Taxi|Car|Vehicle|Rickshaw", case=False, na=False)
    missing_km_rows = df[road_travel_mask & (df["Kilometer"] == 0)]

    if not missing_km_rows.empty:
        st.warning(f"⚠️ Found {len(missing_km_rows)} journey(s) by Road/Auto without Kilometers.")
        with st.expander("📝 Quickly Add Missing Kilometers & Rates", expanded=True):
            st.caption("Fill these details here, and they will automatically update the main table.")
            
            # Create a mini form for quick entry
            for idx, row in missing_km_rows.iterrows():
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                with c1:
                    st.write(f"**{row['Departure_Place']}** ➝ **{row['Arrival_Place']}** ({row['Mode_of_Travel']})")
                with c2:
                    km_val = st.number_input(f"KM (Row {idx})", min_value=0.0, key=f"km_{idx}")
                with c3:
                    rate_val = st.number_input(f"Rate/KM (Row {idx})", value=12.0, key=f"rate_{idx}")
                with c4:
                    if st.button("Update", key=f"btn_{idx}"):
                        st.session_state['ta_calculation_df'].at[idx, "Kilometer"] = km_val
                        st.session_state['ta_calculation_df'].at[idx, "Rate_per_KM"] = rate_val
                        st.rerun()

    # 3. Auto-Calculate Column 13 (KM * Rate)
    # We apply this calculation every time before showing the table
    st.session_state['ta_calculation_df']["Mileage_Total"] = (
        st.session_state['ta_calculation_df']["Kilometer"] * st.session_state['ta_calculation_df']["Rate_per_KM"]
    )

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
            
            "Ticket_Price_Rate": st.column_config.NumberColumn("9. Rate (Rs.)", format="₹ %.2f"),
            "Actual_Ticket_Amount": st.column_config.NumberColumn("10. Ticket Total (Rs.)", format="₹ %.2f"),
            
            "Kilometer": st.column_config.NumberColumn("11. KM", format="%.1f km"),
            "Rate_per_KM": st.column_config.NumberColumn("12. Rate/KM (Rs.)", format="₹ %.2f"),
            
            "Mileage_Total": st.column_config.NumberColumn(
                "13. Total (KM*Rate)", 
                format="₹ %.2f", 
                disabled=True, 
                help="Auto-calculated: Col 11 * Col 12"
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
# TAB 2: DA Calculation (Existing Logic)
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
