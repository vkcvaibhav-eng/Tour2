import streamlit as st
import pandas as pd

st.title("📝 Review & Calculate")

if 'extracted_data' not in st.session_state:
    st.warning("No data found. Please go to 'Upload & Extract' first.")
    st.stop()

data = st.session_state['extracted_data']

# --- Section 1: Manual Edit (Arrival/Dispatch) ---
st.subheader("1. Edit Trip Details (Arrival & Dispatch)")
st.caption("Verify extracted dates and times against your Tour Diary.")

# Flatten the structure for editing
if 'trip_df' not in st.session_state:
    # Initialize with extracted data if available, else empty
    initial_data = data.get('tour_data', [{'date': '', 'from': '', 'to': ''}])
    st.session_state['trip_df'] = pd.DataFrame(initial_data)

edited_trip_df = st.data_editor(st.session_state['trip_df'], num_rows="dynamic", use_container_width=True)

# --- Section 2: TA/DA Calculation Matrix ---
st.subheader("2. TA/DA Calculation Preview")
st.markdown("This table corresponds to the **1 to 16 column** format required.")

# Create the specific 16-column structure requested
# Columns strictly based on your image: Sr No, 1-16 cols, Total, Purpose, Note
columns = [
    "Sr. No", 
    "Departure Date", "Departure Time", "Arrival Date", "Arrival Time", # Cols 1-4
    "From", "To", "Mode of Travel", "Class", # Cols 5-8
    "Fare Amount", "Ticket No", "Daily Allowance", "Local Taxi", # Cols 9-12
    "Hotel Charges", "Total Claimed", "Admissible Amt", "Remark", # Cols 13-16
    "Total Sum", "Purpose (Justification)", "Note"
]

# Create empty dataframe with these columns if not exists
if 'calc_df' not in st.session_state:
    st.session_state['calc_df'] = pd.DataFrame(columns=columns)

# Allow user to fill the 16 columns
final_df = st.data_editor(st.session_state['calc_df'], num_rows="dynamic", height=400)

if st.button("Confirm Calculation"):
    st.session_state['final_export_data'] = final_df
    st.success("Calculation confirmed. Ready for Export.")
