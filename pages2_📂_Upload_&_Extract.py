import streamlit as st
import utils

st.title("📂 Upload & Extract Data")

if 'gemini_api_key' not in st.session_state:
    st.error("Please set your Gemini API Key in the Settings page first.")
    st.stop()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Personal Documents")
    salary_slip = st.file_uploader("Salary Slip", type=['pdf', 'jpg', 'png'])
    tour_diary = st.file_uploader("Tour Diary", type=['pdf', 'jpg', 'png'])

with col2:
    st.subheader("Expense Documents")
    tickets = st.file_uploader("Tickets / Fare Enquiry", accept_multiple_files=True)
    hotel_bills = st.file_uploader("Hotel / Guest House Bills", accept_multiple_files=True)

st.markdown("---")

if st.button("🚀 Analyze & Extract Data"):
    with st.spinner("AI is reading your documents..."):
        # Combine all files logic would go here
        # This calls the placeholder function in utils.py
        extracted_data = utils.call_gemini_extraction(
            st.session_state['gemini_api_key'], 
            [salary_slip, tour_diary], 
            "Extract TA DA details"
        )
        
        st.session_state['extracted_data'] = extracted_data
        st.success("Extraction Complete! Proceed to the 'Review & Calculate' page.")
        st.json(extracted_data) # Show raw preview