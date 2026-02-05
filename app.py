import streamlit as st
import pandas as pd
from fpdf import FPDF
from docx import Document
from datetime import datetime

# --- CONFIGURATION & STYLING ---
st.set_page_config(page_title="NAU TA/DA Claim Assistant", layout="wide")

# --- DATA STRUCTURES ---
if "tour_data" not in st.session_state:
    st.session_state.tour_data = pd.DataFrame(columns=[
        "Date", "Arrival_Place", "Arrival_Time", "Departure_Place", "Departure_Time", 
        "Mode", "Class", "Vehicle_Details", "Distance_KM", "Ticket_Amount", "Enquiry_Fare"
    ])

if "stay_data" not in st.session_state:
    st.session_state.stay_data = pd.DataFrame(columns=[
        "City", "Class_of_City", "CheckIn_Date", "CheckOut_Date", "Hotel_Bill_Amt"
    ])

# --- HELPER FUNCTIONS ---
def calculate_da(days, city_class, pay_level):
    # Logic derived from Revised-provision-of-TD-DA-2024.pdf 
    # Simplified example rates for illustration; replace with exact table values
    rates = {"X": 1000, "Y": 800, "Z": 500}
    return days * rates.get(city_class, 500)

# --- APP UI ---
st.title("📋 NAU TA/DA Tour Diary & Claim System")

tab_upload, tab_edit, tab_calc, tab_export = st.tabs([
    "📤 Upload/Extract", "📝 Editable Tour Diary", "🧮 TA/DA Calculation", "📄 Export Report"
])

with tab_upload:
    st.subheader("Upload Travel Documents")
    uploaded_files = st.file_uploader("Upload tickets or bills", accept_multiple_files=True)
    if st.button("Extract Data (AI)"):
        st.info("AI extraction would process files here...")

with tab_edit:
    st.subheader("Edit Tour & Journey Details")
    
    # Editable Journey Table
    st.write("### 1. Journey Details")
    edited_tour = st.data_editor(
        st.session_state.tour_data, 
        num_rows="dynamic", 
        key="tour_editor",
        column_config={
            "Mode": st.column_config.SelectboxColumn(options=["Railway", "Bus", "Flight", "Road (Private)", "Road (Public)"]),
            "Vehicle_Details": st.column_config.TextColumn("Vehicle Details (Diesel/Petrol/CC)"),
        }
    )
    
    # Editable Stay/Hotel Table
    st.write("### 2. Stay & Hotel Details")
    edited_stay = st.data_editor(
        st.session_state.stay_data, 
        num_rows="dynamic", 
        key="stay_editor",
        column_config={
            "Class_of_City": st.column_config.SelectboxColumn(options=["X", "Y", "Z"])
        }
    )

with tab_calc:
    st.subheader("Calculation Breakdown")
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("**TA Rule Applied:** Reimbursement is based on actual fare or official enquiry if private vehicle is used. ")
        # TA Calculation Logic
        total_ta = edited_tour["Ticket_Amount"].sum() + edited_tour["Enquiry_Fare"].sum()
        st.metric("Total TA Admissible", f"₹{total_ta}")

    with col2:
        st.info("**DA Rule Applied:** Based on pay level and city classification (X/Y/Z) as per Circular 1734. [cite: 3]")
        # DA Calculation Logic
        total_da = 0 # Logic to iterate through stay days
        st.metric("Total DA Admissible", f"₹{total_da}")

with tab_export:
    st.subheader("Final Export")
    
    if st.button("Generate Word (Docx) Tour Diary"):
        doc = Document()
        doc.add_heading('University Official Tour Diary', 0)
        
        # Adding definitions as requested
        doc.add_heading('Definitions & Rules', level=1)
        doc.add_paragraph("Mode of Transport: Actual means of conveyance used (Railway/Bus/Flight). ")
        doc.add_paragraph("Road Travel: Use of private vehicle restricted to public transport fare enquiry. ")
        
        # Add Tables
        table = doc.add_table(rows=1, cols=len(edited_tour.columns))
        # (Table generation logic here...)
        
        doc.save("Tour_Diary.docx")
        with open("Tour_Diary.docx", "rb") as file:
            st.download_button("Download Docx", file, "Tour_Diary.docx")
