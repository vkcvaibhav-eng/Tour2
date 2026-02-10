import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from io import BytesIO

st.set_page_config(layout="wide", page_title="Step 5: Final Gujarati Export")
st.title("🇮🇳 Step 5: Final Gujarati Export (A2 Size)")

st.markdown("---")
st.info("Generates the 1-19 column table on a 42cm x 59.4cm page, using the exact headers from your sample.")

# --- HELPER FUNCTIONS ---

def set_cell_margins(cell, top=0, start=0, bottom=0, end=0):
    """Removes margins from table cells to fit text tightly."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('start', start), ('bottom', bottom), ('end', end)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def format_header_cell(cell, text, font_size=9, bold=True):
    """Formats a header cell with specific font and alignment."""
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
    run.text = text
    run.font.bold = bold
    run.font.size = Pt(font_size)
    run.font.name = 'Arial Unicode MS'  # Crucial for Gujarati
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

def create_gujarati_table(ta_data):
    doc = Document()
    
    # 1. SETUP PAGE SIZE (A2 Portrait: 42cm x 59.4cm)
    section = doc.sections[0]
    section.page_width = Cm(42)
    section.page_height = Cm(59.4)
    
    # Narrow margins to maximize table space
    section.left_margin = Cm(1.0)
    section.right_margin = Cm(1.0)
    section.top_margin = Cm(1.0)
    section.bottom_margin = Cm(1.0)

    # 2. DOCUMENT TITLE
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("મુસાફરી ભથ્થાનું બિલ (Travelling Allowance Bill)")
    run.bold = True
    run.font.size = Pt(20)
    run.font.name = 'Arial Unicode MS'

    # 3. CREATE 19-COLUMN TABLE
    table = doc.add_table(rows=3, cols=19)
    table.style = 'Table Grid'
    table.autofit = False 
    
    # Set Column Widths (Approximation to fit 40cm width)
    # Date/Time cols are small, Place is med, Amounts are small
    widths = [1.8, 1.8, 1.5, 1.8, 1.8, 1.5, 1.5, 1.5, 1.5, 2.0, 1.5, 1.5, 2.0, 1.5, 1.5, 2.0, 1.5, 2.0, 2.5]
    for i, width in enumerate(widths):
        if i < 19:
            for row in table.rows:
                row.cells[i].width = Cm(width)

    # --- ROW 1: MAIN HEADERS (Merged) ---
    # Merge cells for grouped headers
    # 0-2 (Depart), 3-5 (Arrive), 6 (Mode), 7 (Class), 8 (Ticket No), 9 (Fare), 
    # 10-12 (Road Details), 13 (Road Amt), 14-17 (DA), 18 (Total) -- Adjusting to map 19 cols exactly
    
    # Header Mapping based on your request (1-19)
    # 1,2,3: Depart | 4,5,6: Arrive | 7: Mode | 8: Class | 9: Tkt No | 10: Fare 
    # 11: KM | 12: Rate | 13: Road Amt | 14: Days | 15: Rate | 16: Amt | 17: Less | 18: Net DA | 19: Grand Total
    
    row1 = table.rows[0].cells
    
    # Merges
    row1[0].merge(row1[2])  # Departure
    row1[3].merge(row1[5])  # Arrival
    
    format_header_cell(row1[0], "ઉપડ્યા (Departure)")
    format_header_cell(row1[3], "પહોંચ્યા (Arrival)")
    format_header_cell(row1[6], "વાહન\n(Mode)")
    format_header_cell(row1[7], "વર્ગ\n(Class)")
    format_header_cell(row1[8], "ટિકિટ નં/દર\n(Tkt No)")
    format_header_cell(row1[9], "ભાડું (A)\n(Fare)")
    format_header_cell(row1[10], "રોડ કિમી\n(Road KM)")
    format_header_cell(row1[11], "દર\n(Rate)")
    format_header_cell(row1[12], "રોડ રકમ (B)\n(Road Amt)")
    format_header_cell(row1[13], "દિવસો\n(Days)")
    format_header_cell(row1[14], "દર\n(Rate)")
    format_header_cell(row1[15], "રકમ\n(Amount)")
    format_header_cell(row1[16], "કપાત\n(Less)")
    format_header_cell(row1[17], "કુલ DA (C)\n(Net DA)")
    format_header_cell(row1[18], "કુલ રકમ (A+B+C)\n(Grand Total)")

    # --- ROW 2: SUB HEADERS ---
    row2 = table.rows[1].cells
    sub_headers = [
        "સ્થળ\n(Place)", "તારીખ\n(Date)", "સમય\n(Time)",
        "સ્થળ\n(Place)", "તારીખ\n(Date)", "સમય\n(Time)",
        "", "", "", "Rs.",
        "KM", "Rs.", "Rs.",
        "No.", "Rs.", "Rs.", "Rs.", "Rs.", "Rs."
    ]
    
    for i, text in enumerate(sub_headers):
        format_header_cell(row2[i], text, font_size=8, bold=False)

    # --- ROW 3: COLUMN NUMBERS (1 to 19) ---
    row3 = table.rows[2].cells
    for i in range(19):
        format_header_cell(row3[i], str(i + 1), font_size=10, bold=True)

    # --- POPULATE DATA (Row 4 onwards) ---
    # We pull directly from st.session_state['final_ta_data']
    
    grand_total_sum = 0.0

    if not ta_data.empty:
        for idx, row in ta_data.iterrows():
            new_row = table.add_row().cells
            
            # Helper to safely get string
            def get_val(col_name):
                return str(row.get(col_name, ""))
            
            # Helper to safely get float
            def get_float(col_name):
                try:
                    return float(row.get(col_name, 0))
                except:
                    return 0.0

            # 1-3 Departure
            new_row[0].text = get_val("1. Departure Place")
            new_row[1].text = get_val("2. Departure Date")
            new_row[2].text = get_val("3. Departure Time")
            
            # 4-6 Arrival
            new_row[3].text = get_val("4. Arrival Place")
            new_row[4].text = get_val("5. Arrival Date")
