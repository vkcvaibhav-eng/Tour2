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
tab1, tab2 = st.tabs(["🚆 TA Calculation (Tickets/Fuel)", "📅 DA Calculation (Allowance)"])

# === TAB 1: TA Calculation ===
with tab1:
    st.subheader("Transport Allowance (Tickets / KM)")
    st.caption("Enter ticket prices for the journeys defined in your diary.")
    
    # Prepare TA dataframe based on the diary rows
    # We only need rows where travel actually happened (not stays)
    # A simple way is to copy the diary and add "Fare" columns
    if 'ta_calculation_df' not in st.session_state:
        ta_df = diary_df.copy()
        ta_df["Ticket_No"] = ""
        ta_df["Class"] = "II/III"
        ta_df["Fare_Amount"] = 0.0
        ta_df["Remark"] = ""
        st.session_state['ta_calculation_df'] = ta_df

    # Edit the TA values
    st.session_state['ta_calculation_df'] = st.data_editor(
        st.session_state['ta_calculation_df'],
        use_container_width=True,
        hide_index=True,
        column_order=["Departure_Place", "Arrival_Place", "Mode_of_Travel", "Class", "Ticket_No", "Fare_Amount", "Remark"]
    )
    
    # Calculate Total TA
    total_ta = st.session_state['ta_calculation_df']["Fare_Amount"].sum()
    st.metric("Total TA Claim", f"₹ {total_ta:,.2f}")


# === TAB 2: DA Calculation ===
with tab2:
    st.subheader("Daily Allowance (DA)")
    st.caption("The system will calculate duration based on your verified dates/times.")

    if st.button("🔄 Recalculate DA based on Diary"):
        # Logic to calculate duration (End Time - Start Time)
        # This is a placeholder for your duration logic
        da_data = []
        for index, row in diary_df.iterrows():
            # You would add your logic here to calculate 12hr/24hr blocks
            # For now, we just pass the row to be editable
            da_data.append({
                "Date": row['Arrival_Date'], # Usually calculated per day
                "Stay_At": row['Arrival_Place'],
                "Duration_Hours": 0, # Placeholder for auto-calc
                "Pay_Level_Rate": 0, # Placeholder for rate fetch
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
    # Save everything for Page 5 Export
    st.session_state['final_ta_data'] = st.session_state['ta_calculation_df']
    st.session_state['final_da_data'] = st.session_state.get('da_calculation_df', pd.DataFrame())
    st.success("Calculations Saved! Ready for Export on Page 5.")
