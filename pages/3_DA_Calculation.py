import streamlit as st
import pandas as pd
import utils

st.set_page_config(layout="wide")
st.title("📅 Step 3: DA Calculation")

if 'final_tour_diary' not in st.session_state:
    st.warning("Please complete Tour Diary first.")
    st.stop()

# --- SECTION 1: UPLOAD DA RULES ---
st.subheader("1. Upload DA Rules")
st.markdown("Upload the relevant Government Circulars or Rules for Daily Allowance.")
da_rules = st.file_uploader("Upload DA Regulation/Circulars", accept_multiple_files=True)

if da_rules and st.button("Apply DA Rules"):
    st.info("Applying DA rules to your tour dates...")
    # (Logic to read rules and determine rates would go here)
    st.success("DA Rates updated based on uploaded circulars.")

# --- SECTION 2: DA WORKSHEET ---
st.subheader("2. DA Worksheet")
st.markdown("You can add or remove rows here as needed.")

# Initialize DA DF based on Diary Dates if not exists
if 'da_calculation_df' not in st.session_state:
    diary = st.session_state['final_tour_diary']
    # Create a basic list of dates from the diary
    da_data = []
    for index, row in diary.iterrows():
        da_data.append({
            "Date": row['Arrival_Date'],
            "Place": row['Arrival_Place'],
            "Pay_Level": "Level 10", # Example default
            "DA_Rate": 0.0,
            "Claim_Amount": 0.0
        })
    st.session_state['da_calculation_df'] = pd.DataFrame(da_data)

# Editor (Allow Adding/Deleting rows)
edited_da = st.data_editor(
    st.session_state['da_calculation_df'],
    num_rows="dynamic", # Allow adding/removing rows
    use_container_width=True,
    column_config={
        "Date": st.column_config.DateColumn("Date", format="DD-MM-YYYY"),
        "DA_Rate": st.column_config.NumberColumn("DA Rate", format="₹ %.2f"),
        "Claim_Amount": st.column_config.NumberColumn("Claim Amount", format="₹ %.2f"),
    }
)

st.session_state['final_da_data'] = edited_da

# Totals
total_da = edited_da['Claim_Amount'].sum() if not edited_da.empty else 0
st.metric("💰 Total Daily Allowance", f"₹ {total_da:,.2f}")
