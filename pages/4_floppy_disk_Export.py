import streamlit as st
import utils
from io import BytesIO

st.title("💾 Export Final Document")

if 'final_diary' not in st.session_state:
    st.warning("No data ready. Please click 'Confirm All' on the Review page.")
    st.stop()

st.success("Data is ready for generation.")

if st.button("Generate Word Document (A3)"):
    # Generate the document with all 3 DataFrames
    doc = utils.create_word_doc(
        st.session_state['final_diary'],
        st.session_state['final_ta'],
        st.session_state['final_da']
    )
    
    # Save to buffer
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    st.download_button(
        label="⬇️ Download TA_DA_Claim.docx",
        data=buffer,
        file_name="TA_DA_Claim_Form.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
