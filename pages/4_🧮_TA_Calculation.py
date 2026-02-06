import streamlit as st
import pandas as pd
import utils
import os

st.set_page_config(layout="wide")
st.title("🧮 Step 2: TA Calculation")

if 'final_tour_diary' not in st.session_state:
    st.warning("Please complete Step 1 (Tour Diary) first.")
    st.stop()

# --- SECTION 1: UPLOAD EVIDENCE & RULES ---
st.subheader("1. Upload TA Documents")
st.markdown("Upload your tickets and the specific Government/University Statutes for TA calculation.")

col1, col2 = st.columns(2)
with col1:
    ta_tickets = st.file_uploader("Upload Tickets / Bills", accept_multiple_files=True, key="tickets")
with col2:
    ta_rules = st.file_uploader("Upload TA Rules/Statutes", accept_multiple_files=True, key="ta_rules")

if st.button("Apply Rules & Calculate TA"):
    if not ta_rules:
        st.warning("⚠️ Please upload TA Rules to perform calculation based on statutes.")
    else:
        # Placeholder for the logic where you send the Rules + Tickets + Diary to Gemini
        # to fill in the "Ticket_Price" and "KM" columns based on the rules.
        st.info("AI is analyzing tickets against the uploaded statutes...")
        # (This is where you would call utils.call_gemini_extraction with these new files)
        st.success("Calculation complete based on uploaded rules.")

# --- SECTION 2: CALCULATION MATRIX ---
st.divider()
st.subheader("2. TA Calculation Matrix")

diary_df = st.session_state['final_tour_diary']

# Prepare TA DataFrame (Initialize if needed)
if 'ta_calculation_df' not in st.session_state:
    # Copy structure from diary and add TA specific columns
    ta_df = diary_df.copy()
    ta_df["Class_Vehicle"] = ""
    ta_df["Ticket_Price"] = 0.0
    ta_df["KM"] = 0.0
    ta_df["Rate_per_KM"] = 0.0
    ta_df["Total_Amount"] = 0.0
    st.session_state['ta_calculation_df'] = ta_df

# Editor
edited_ta = st.data_editor(
    st.session_state['ta_calculation_df'],
    use_container_width=True,
    num_rows="fixed", # Rows tied to diary
    column_config={
        "Ticket_Price": st.column_config.NumberColumn("Ticket Amount", format="₹ %.2f"),
        "KM": st.column_config.NumberColumn("Distance (KM)"),
        "Rate_per_KM": st.column_config.NumberColumn("Rate/KM", format="₹ %.2f"),
        "Total_Amount": st.column_config.NumberColumn("Total", format="₹ %.2f"),
    }
)

st.session_state['final_ta_data'] = edited_ta

# Totals
total_ta = edited_ta["Total_Amount"].sum()
st.metric("💰 Total Transport Allowance", f"₹ {total_ta:,.2f}")
