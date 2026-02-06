import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("📅 DA Calculation (Daily Allowance)")

# Check if Page 4 was completed
if 'final_ta_data' not in st.session_state:
    st.error("Please finish 'Page 4: TA Calculation' first.")
    st.stop()

diary_df = st.session_state['final_tour_diary']

st.info("Step 2: Calculate Daily Allowance based on your stay duration.")

# =========================================================
# DA LOGIC
# =========================================================

# Initialize if not exists
if 'da_calculation_df' not in st.session_state:
    da_data = []
    for index, row in diary_df.iterrows():
        # Only add rows that are typically relevant for DA (Arrivals)
        da_data.append({
            "Date": row['Arrival_Date'], 
            "Stay_At": row['Arrival_Place'],
            "Duration_Hours": 0, 
            "Pay_Level_Rate": 0, 
            "DA_Claimed": 0
        })
    st.session_state['da_calculation_df'] = pd.DataFrame(da_data)

if st.button("🔄 Reset / Recalculate DA List"):
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

# =========================================================
# EDITOR
# =========================================================
st.markdown("### 📋 Edit DA Details")

edited_da = st.data_editor(
    st.session_state['da_calculation_df'],
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "Date": st.column_config.DateColumn("Date", format="DD-MM-YYYY"),
        "Stay_At": st.column_config.TextColumn("Place of Stay"),
        "Duration_Hours": st.column_config.NumberColumn("Hours", help="Total hours away from HQ"),
        "Pay_Level_Rate": st.column_config.NumberColumn("DA Rate", format="₹ %.2f"),
        "DA_Claimed": st.column_config.NumberColumn("Amount Claimed", format="₹ %.2f")
    }
)

st.session_state['da_calculation_df'] = edited_da

# =========================================================
# TOTALS & NAVIGATION
# =========================================================
total_da = st.session_state['da_calculation_df']["DA_Claimed"].sum()

st.divider()
st.metric("💰 Total DA Claim", f"₹ {total_da:,.2f}")

st.markdown("---")
if st.button("💾 Save & Go to Export (Page 6)"):
    st.session_state['final_da_data'] = st.session_state['da_calculation_df']
    st.switch_page("pages/6_floppy_disk_Export.py")
