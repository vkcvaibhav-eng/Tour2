import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from io import BytesIO

st.set_page_config(layout="wide", page_title="Step 5: Gujarati Export (A2)")
st.title("🇮🇳 Step 5: Gujarati Final Export (A2 Size)")

st.markdown("---")
st.info("Generates the final 1-19 column Gujarati format on a 42cm x 59.4cm page.")

# --- HELPER FUNCTIONS ---

def set_cell_margins(cell, top=0, start=0, bottom=0, end=0):
    """Removes margins from table cells to fit more text."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    
    for m, val in [('top', top), ('start', start), ('bottom', bottom), ('end', end)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    
    tcPr.append(tcMar)

def create_gujarati_doc(tour_data, ta_data, da_data):
    doc = Document()
    
    # 1. SETUP PAGE SIZE (A2: 42cm x 59.4cm)
    section = doc.sections[0]
    section.page_width = Cm(42)
    section.page_height = Cm(59.4)
    
    # Margins (Narrow to fit 19 columns)
    section.left_margin = Cm(1.27)
    section.right_margin = Cm(1.27)
    section.top_margin = Cm(1.27)
    section.bottom_margin = Cm(1.27)

    # 2. TITLE SECTION (Gujarati)
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial Unicode MS'  # Good for Gujarati
    font.size = Pt(11)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("મુસાફરી ભથ્થાનું બિલ (TA/DA Bill)")
    run.bold = True
    run.font.size = Pt(24)

    # Employee Info (Placeholder - User fills usually, or we take from profile if available)
    info_p = doc.add_paragraph()
    info_p.add_run("\nકર્મચારીનું નામ: _______________________      હોદ્દો: _______________________\n")
    info_p.add_run("હેડ ક્વાર્ટર: _______________________           પગાર: _______________________\n")

    # 3. CREATE THE 19-COLUMN TABLE
    # Columns mapping based on 'ok.pdf' logic:
    # 1-3: Depart | 4-6: Arrive | 7: Mode | 8: Class | 9: Tkt No | 10: Fare (A)
    # 11: KM | 12: Rate | 13: Road Amt (B) | 14: Days | 15: Rate | 16-17: Calc | 18: DA Tot (C) | 19: Total (A+B+C)
    
    table = doc.add_table(rows=2, cols=19)
    table.style = 'Table Grid'
    table.autofit = False 
    
    # Set rough column widths (total 40cm available approx)
    # We distribute them: Dates need space, Amounts need space, small cols for others.
    # This is an approximation for A2 width.
    for col in table.columns:
        col.width = Cm(2.0) 

    # --- HEADERS ---
    # Row 1: Main Headers
    hdr_cells = table.rows[0].cells
    
    headers_guj = [
        "ઉપડ્યા (Departure)", "", "", 
        "પહોંચ્યા (Arrival)", "", "",
        "વાહન", "વર્ગ", "ટિકિટ નં", "ભાડું (A)",
        "રોડ કિમી", "દર", "રોડ રકમ (B)",
        "દિવસો", "દર", "રકમ", "કપાત", "કુલ DA (C)",
        "કુલ રકમ (A+B+C)"
    ]
    
    # Row 2: Sub Headers (Date/Time/Place) & Column Numbers
    sub_cells = table.rows[1].cells
    sub_headers = [
        "સ્થળ", "તારીખ", "સમય",
        "સ્થળ", "તારીખ", "સમય",
        "Mode", "Class", "No/Rate", "Rs.",
        "KM", "Rate", "Rs.",
        "Days", "Rate", "Amt", "Less", "Final DA",
        "Total"
    ]
    
    # Column Numbers Row (Row 3)
    row_nums = table.add_row().cells
    
    for i in range(19):
        # Set Top Header text
        if i < len(headers_guj):
            hdr_cells[i].text = headers_guj[i]
        
        # Set Sub Header text
        sub_cells[i].text = sub_headers[i]
        
        # Set Column Numbers (1 to 19)
        row_nums[i].text = str(i + 1)
        
        # Formatting
        for row in [table.rows[0], table.rows[1], table.rows[2]]:
            cell = row.cells[i]
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.runs[0] if p.runs else p.add_run()
            run.font.bold = True
            run.font.size = Pt(9)
            set_cell_margins(cell, top=50, bottom=50)

    # --- POPULATE DATA ---
    # We iterate through the TA Data (Ticket/Road) and merge with DA info
    
    # Note: This logic assumes 'final_ta_data' has the rows. 
    # We need to calculate totals for Col 10, 13, 18.
    
    grand_total_claim = 0.0

    if not ta_data.empty:
        for idx, row in ta_data.iterrows():
            new_row = table.add_row().cells
            
            # --- Extract Data ---
            # 1-3 Departure
            new_row[0].text = str(row.get("1. Departure Place", ""))
            new_row[1].text = str(row.get("2. Departure Date", ""))
            new_row[2].text = str(row.get("3. Departure Time", ""))
            
            # 4-6 Arrival
            new_row[3].text = str(row.get("4. Arrival Place", ""))
            new_row[4].text = str(row.get("5. Arrival Date", ""))
            new_row[5].text = str(row.get("6. Arrival Time", ""))
            
            # 7-8 Mode/Class
            new_row[6].text = str(row.get("7. Mode", ""))
            new_row[7].text = str(row.get("8. Class", ""))
            
            # 9-10 Fare (Ticket)
            tkt_price = pd.to_numeric(row.get("9. Ticket Price/Rate (Rs.)", 0), errors='coerce')
            tkt_amt = pd.to_numeric(row.get("10. Actual Total Amount of Ticket (Rs.)", 0), errors='coerce')
            new_row[8].text = f"{tkt_price:.2f}"
            new_row[9].text = f"{tkt_amt:.2f}"
            
            # 11-13 Road Mileage
            km = pd.to_numeric(row.get("11. KM", 0), errors='coerce')
            rate = pd.to_numeric(row.get("12. Rate (Rs.) (Auto/Taxi/Pvt)", 0), errors='coerce')
            road_amt = km * rate # Calculate explicitly to be safe
            
            new_row[10].text = f"{km:.1f}"
            new_row[11].text = f"{rate:.1f}"
            new_row[12].text = f"{road_amt:.2f}"
            
            # 14-18 DA Calculation (Matching logic)
            # We need to find if there is a DA entry for this date/row. 
            # For simplicity in this table row, we might leave blank or fill if data aligns perfectly.
            # Assuming 'da_data' is a summary, we might just put the total DA at the end or distributed.
            # STRATEGY: If this row represents a full day halt, we add DA. 
            # Ideally, user edits this in Word. We will fill 0 for now unless we have complex mapping.
            
            da_days = 0
            da_rate = 0
            da_total = 0 # This is Col 18
            
            # (Optional: Logic to fetch DA from da_data based on date matching could go here)
            
            new_row[13].text = "" # Days
            new_row[14].text = "" # Rate
            new_row[15].text = "" # Amount
            new_row[16].text = "" # Less
            new_row[17].text = "" # Final DA (18)
            
            # 19 Total (10 + 13 + 18)
            row_total = tkt_amt + road_amt + da_total
            new_row[18].text = f"{row_total:.2f}"
            
            grand_total_claim += row_total
            
            # Formatting
            for cell in new_row:
                cell.paragraphs[0].style.font.size = Pt(10)

    # --- SUMMARY ROW ---
    sum_row = table.add_row().cells
    sum_row[0].text = "કુલ (Total)"
    sum_row[18].text = f"₹ {grand_total_claim:.2f}"
    
    # Merge first few cells for Total label
    sum_row[0].merge(sum_row[9]) # Merge up to col 10 roughly

    return doc

# --- MAIN UI ---

if st.button("📄 Generate Gujarati A2 Document"):
    # Check session state
    if 'final_ta_data' in st.session_state:
        
        # Load data
        ta_df = st.session_state['final_ta_data']
        da_df = st.session_state.get('final_da_data', pd.DataFrame())
        tour_df = st.session_state.get('final_tour_diary', pd.DataFrame())

        try:
            doc = create_gujarati_doc(tour_df, ta_df, da_df)
            
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            
            st.download_button(
                label="⬇️ Download Gujarati_TA_Bill_A2.docx",
                data=buffer,
                file_name="Gujarati_TA_Bill_A2.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.success("✅ Document generated successfully! Print on A2 paper or Plotter.")
            
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.error("⚠️ No TA Data found. Please complete Step 2 first.")
