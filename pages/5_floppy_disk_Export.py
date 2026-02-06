import streamlit as st
import utils
from io import BytesIO

st.title("💾 Export Final Document (1-16 Format)")

# Check if data exists from Page 3
if 'final_diary' not in st.session_state:
    st.warning("No data ready. Please go to 'Review & Calculate' and click 'Confirm All'.")
    st.stop()

st.info("Generating the '1 to 16' Column format based on your uploaded CSV structure.")

if st.button("Generate Final Word Document"):
    # Call the new complex function
    doc = utils.create_complex_claim_form(
        st.session_state['final_diary'],
        st.session_state['final_ta'],
        st.session_state['final_da']
    )
    
    # Save to buffer
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    st.download_button(
        label="⬇️ Download TA_DA_Bill.docx",
        data=buffer,
        file_name="TA_DA_Claim_Final.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
