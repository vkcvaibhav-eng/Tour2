import streamlit as st
import utils
from io import BytesIO

st.set_page_config(layout="wide")
st.title("💾 Step 4: Export Final Document")

st.markdown("---")
st.info("Generates the final claim form based on Tour Diary, TA, and DA data.")

if st.button("📄 Generate Word Document"):
    # Check if data exists
    if 'final_tour_diary' in st.session_state and \
       'final_ta_data' in st.session_state and \
       'final_da_data' in st.session_state:
        
        try:
            doc = utils.create_complex_claim_form(
                st.session_state['final_tour_diary'],
                st.session_state['final_ta_data'],
                st.session_state['final_da_data']
            )
            
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            
            st.download_button(
                label="⬇️ Download TA_DA_Claim.docx",
                data=buffer,
                file_name="TA_DA_Claim_Final.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.balloons()
            
        except Exception as e:
            st.error(f"Error generating document: {e}")
            
    else:
        st.error("⚠️ Data missing. Please complete Steps 1, 2, and 3.")
