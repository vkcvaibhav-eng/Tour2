import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from io import BytesIO

# --- PAGE CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Step 5: Final Gujarati Export")
st.title("🇮🇳 Step 5: Final Gujarati Export (A2 Size)")
st.markdown("---")

# --- DATA CONNECTION (Connects to Step 4 Data) ---
# We retrieve the data directly from the session state used in Step 4
if 'final_ta_data' in st.session_state:
    df_ta = st.session_state['final_ta_data']
    st.success(f"✅ Connected to Final Table: {len(df_ta)} rows loaded.")
else:
    st.warning("⚠️ No data found from Step 4. Please complete previous steps first.")
    df_ta = pd.DataFrame()

if 'final_da_data' in st.session_state:
    df_da = st.session_state['final_da_data']
else:
    df_da = pd.DataFrame()

# --- HELPER FUNCTIONS FOR WORD ---

def set_cell_margins(cell, top=10, start=10, bottom=10, end=10):
    """Sets custom margins for a cell to fit more text."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('start', start), ('bottom', bottom), ('end', end)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def format_cell_text(cell, text, font_size=9, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER):
    """Formats text inside a cell with Arial Unicode MS for Gujarati support."""
    paragraph = cell.paragraphs[0]
    paragraph.alignment = align
    run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
    run.text = str(text)
    run.font.bold = bold
    run.font.size = Pt(font_size)
    run.font.name = 'Arial Unicode MS'  # Required for Gujarati
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

def create_gujarati_doc(ta_data, da_data):
    doc = Document()
    
    # 1. PAGE SETUP: A2 PORTRAIT (42cm x 59.4cm)
    section = doc.sections[0]
    section.page_width = Cm(42)
    section.page_height = Cm(59.4)
    section.left_margin = Cm(1.27)
    section.right_margin = Cm(1.27)
    section.top_margin = Cm(1.27)
    section.bottom_margin = Cm(1.27)

    # 2. TITLE
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("મુસાફરી ભથ્થાનું બિલ (Travelling Allowance Bill)")
    run.bold = True
    run.font.size = Pt(22)
    run.font.name = 'Arial Unicode MS'

    # 3. CREATE TABLE (19 Columns)
    table = doc.add_table(rows=3, cols=19)
    table.style = 'Table Grid'
    table.autofit = False 
    
    # Column Widths (Adjusted for A2 width ~39cm usable)
    # 1-6 (Dates/Times) = 1.8cm
    # 7-8 (Mode/Class) = 1.5cm
    # 9-19 (Amounts) = Mixed
    widths = [
        1.8, 1.8, 1.5,   # 1,2,3 Depart
        1.8, 1.8, 1.5,   # 4,5,6 Arrive
        1.8, 1.5,        # 7 Mode, 8 Class
        1.5, 2.0,        # 9 Tkt No, 10 Fare
        1.5, 1.5, 2.0,   # 11 KM, 12 Rate, 13 Road Amt
        1.5, 1.5, 2.0,   # 14 Days, 15 Rate, 16 Amt
        1.5, 2.0, 2.5    # 17 Less, 18 DA Tot, 19 Total
    ]
    
    # Apply widths
    for row in table.rows:
        for idx, width in enumerate(widths):
            if idx < 19:
                row.cells[idx].width = Cm(width)

    # --- ROW 1: TOP HEADERS (Merged) ---
    r1 = table.rows[0].cells
    
    # Merge Logic
    r1[0].merge(r1[2])  # Depart
    r1[3].merge(r1[5])  # Arrive
    
    # Set Text (Gujarati + English)
    format_cell_text(r1[0], "ઉપડ્યા (Departure)", bold=True, font_size=10)
    format_cell_text(r1[3], "પહોંચ્યા (Arrival)", bold=True, font_size=10)
    format_cell_text(r1[6], "મુસાફરીનો પ્રકાર\n(Mode)", bold=True)
    format_cell_text(r1[7], "વર્ગ\n(Class)", bold=True)
    format_cell_text(r1[8], "ટિકિટ નં\n(Ticket No)", bold=True)
    format_cell_text(r1[9], "ભાડું (A)\n(Fare Rs.)", bold=True)
    format_cell_text(r1[10], "રોડ કિમી\n(Road KM)", bold=True)
    format_cell_text(r1[11], "દર\n(Rate)", bold=True)
    format_cell_text(r1[12], "રોડ રકમ (B)\n(Road Amt)", bold=True)
    format_cell_text(r1[13], "દિવસો\n(DA Days)", bold=True)
    format_cell_text(r1[14], "દર\n(DA Rate)", bold=True)
    format_cell_text(r1[15], "રકમ\n(Amount)", bold=True)
    format_cell_text(r1[16], "કપાત\n(Less)", bold=True)
    format_cell_text(r1[17], "કુલ DA (C)\n(Net DA)", bold=True)
    format_cell_text(r1[18], "કુલ રકમ (A+B+C)\n(Grand Total)", bold=True)

    # --- ROW 2: SUB HEADERS ---
    r2 = table.rows[1].cells
    sub_headers = [
        "સ્થળ (Place)", "તારીખ (Date)", "સમય (Time)",
        "સ્થળ (Place)", "તારીખ (Date)", "સમય (Time)",
        "", "", "", "Rs.",
        "KM", "Rs.", "Rs.",
        "Days", "Rs.", "Rs.", "Rs.", "Rs.", "Rs."
    ]
    for i, txt in enumerate(sub_headers):
        format_cell_text(r2[i], txt, font_size=8)

    # --- ROW 3: COLUMN NUMBERS (1-19) ---
    r3 = table.rows[2].cells
    for i in range(19):
        format_cell_text(r3[i], str(i+1), bold=True)

    # --- ROW 4+: DATA FILLING ---
    # We iterate through the TA Dataframe
    
    total_claim = 0.0

    if not ta_data.empty:
        for index, row in ta_data.iterrows():
            new_row = table.add_row().cells
            
            # Helper for safe numeric conversion
            def get_num(key):
                try:
                    return float(row.get(key, 0))
                except:
                    return 0.0

            # 1-3 Departure
            format_cell_text(new_row[0], row.get("1. Departure Place", ""))
            format_cell_text(new_row[1], row.get("2. Departure Date", ""))
            format_cell_text(new_row[2], row.get("3. Departure Time", ""))

            # 4-6 Arrival
            format_cell_text(new_row[3], row.get("4. Arrival Place", ""))
            format_cell_text(new_row[4], row.get("5. Arrival Date", ""))
            format_cell_text(new_row[5], row.get("6. Arrival Time", ""))

            # 7-8 Mode/Class
            format_cell_text(new_row[6], row.get("7. Mode", ""))
            format_cell_text(new_row[7], row.get("8. Class", ""))

            # 9 Ticket No / Rate
            format_cell_text(new_row[8], row.get("9. Ticket Price/Rate (Rs.)", ""))

            # 10 Fare Amount (A)
            fare_a = get_num("10. Actual Total Amount of Ticket (Rs.)")
            format_cell_text(new_row[9], f"{fare_a:.2f}")

            # 11-13 Road Amount (B)
            km = get_num("11. KM")
            rate = get_num("12. Rate (Rs.) (Auto/Taxi/Pvt)")
            
            # Calculate Road Amt (B)
            road_b = km * rate
            if road_b == 0: road_b = get_num("13. Total (Rs.)") # Fallback
            
            format_cell_text(new_row[10], f"{km:.1f}" if km else "-")
            format_cell_text(new_row[11], f"{rate:.1f}" if rate else "-")
            format_cell_text(new_row[12], f"{road_b:.2f}")

            # 14-18 DA Amount (C)
            # Try to fetch DA data if it exists in the row, otherwise 0
            # (Assuming standard names or matching if you merged previously)
            da_days = get_num("DA_Days")
            da_rate = get_num("DA_Rate")
            da_c = get_num("DA_Amount") # Net DA
            
            format_cell_text(new_row[13], f"{da_days}" if da_days else "")
            format_cell_text(new_row[14], f"{da_rate}" if da_rate else "")
            format_cell_text(new_row[15], f"{da_days*da_rate:.2f}" if da_days and da_rate else "") # Gross DA
            format_cell_text(new_row[16], "") # Less
            format_cell_text(new_row[17], f"{da_c:.2f}" if da_c else "")

            # 19 Grand Total (A + B + C)
            row_total = fare_a + road_b + da_c
            format_cell_text(new_row[18], f"{row_total:.2f}", bold=True)

            total_claim += row_total
            
            # Visual padding
            for cell in new_row:
                set_cell_margins(cell, top=50, bottom=50)

    # --- TOTAL ROW ---
    tot_row = table.add_row().cells
    tot_row[0].merge(tot_row[9]) # Merge first 10 cells
    format_cell_text(tot_row[0], "કુલ સરવાળો (Grand Total)", bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
    
    # Fill Total in Column 19
    format_cell_text(tot_row[18], f"₹ {total_claim:.2f}", bold=True)

    return doc

# --- MAIN UI ---
st.info("The table below matches the 1-19 column structure with Gujarati headers.")

if st.button("📄 Generate & Download Final A2 File"):
    if not df_ta.empty:
        try:
            doc = create_gujarati_doc(df_ta, df_da)
            
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            
            st.download_button(
                label="⬇️ Download Gujarati_Final_A2.docx",
                data=buffer,
                file_name="Gujarati_Final_A2.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.balloons()
        except Exception as e:
            st.error(f"Error generating file: {e}")
    else:
        st.error("Data is empty. Please check Step 2.")
