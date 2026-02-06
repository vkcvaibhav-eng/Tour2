import streamlit as st
import utils
from io import BytesIO

st.set_page_config(layout="wide")
st.title("💾 Export Final Document")

# Check if data exists from Page 5
if 'final_da_data' not in st.session_state:
    st.warning("No DA data ready. Please go to 'Page 5: DA Calculation' and click 'Save'.")
    st.stop()

st.success("✅ All calculations (Tour Diary, TA, DA) are ready.")
st.info("Generating the '1 to 16' Column format based on your entries.")

if st.button("📄 Generate Final Word Document"):
    
    # Check if we have all pieces
    diary = st.session_state.get('final_tour_diary')
    ta = st.session_state.get('final_ta_data')
    da = st.session_state.get('final_da_data')

    if diary is not None and ta is not None and da is not None:
        try:
            # Call the complex function from utils.py
            doc = utils.create_complex_claim_form(diary, ta, da)
            
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
        except Exception as e:
            st.error(f"Error generating document: {e}")
            st.write("Please ensure utils.py has the 'create_complex_claim_form' function.")
    else:
        st.error("Missing data. Please check previous pages.")
