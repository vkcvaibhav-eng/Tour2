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

# --- DATA CONNECTION (Fixed to match Step 4) ---
# We prioritize 'final_18_col_df' (The merged result from Step 4)
if 'final_18_col_df' in st.session_state:
    df_ta = st.session_state['final_18_col_df']
    st.success(f"✅ Connected to Step 4 Final Table: {len(df_ta)} rows loaded.")
elif 'final_ta_data' in st.session_state:
    # Fallback to Step 2 data if Step 4 wasn't run
    df_ta = st.session_state['final_ta_data']
    st.warning("⚠️ Using raw Step 2 data. (Tip: Run Step 4 for the fully merged table).")
else:
    st.error("⚠️ No data found. Please complete Step 4 (Final Table) first.")
    df_ta = pd.DataFrame()

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

def create_gujarati_doc(ta_data):
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
    widths = [
        1.8, 1.8, 1.5,   # 1,2,3 Depart
        1.8, 1.8, 1.5,   # 4,5,6 Arrive
        1.8, 1.5,        # 7 Mode, 8 Class
        1.5, 2.0,        # 9 Tkt No, 10 Fare
        1.5, 1.5, 2.0,   # 11 KM, 12 Rate, 13 Road Amt
        1.5, 1.5, 2.0,   # 14 Days, 15 Rate, 16 Amt
        1.5, 2.0, 2.5    # 17 Less, 18 DA Tot, 19 Total
    ]
    
    for row in table.rows:
        for idx, width in enumerate(widths):
            if idx < 19:
                row.cells[idx].width = Cm(width)

    # --- ROW 1: TOP HEADERS (Merged) ---
    r1 = table.rows[0].cells
    r1[0].merge(r1[2])  # Depart
    r1[3].merge(r1[5])  # Arrive
    
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
    total_claim = 0.0

    if not ta_data.empty:
        # Standardize column names from Step 4
        # We assume the columns come in order 0-18 (which matches 1-19 in output)
        # 0:DepPlace, 1:DepDate, 2:DepTime, 3:ArrPlace, 4:ArrDate, 5:ArrTime, 6:Mode, 7:Class
        # 8:TktPrice, 9:TktTotal(A), 10:KM, 11:Rate, 12:RoadTotal(B)
        # 13:DADays, 14:DARate, 15:DAAmount(C), 16:Total(10+13+15), 17:Purpose
        
        # Note: Step 4 output has ~18 columns. We map them to our 19-column layout.
        # Our 19-column layout: 1-16 matches. 
        # Col 17 in output is "Less". Col 18 is "Net DA". Col 19 is "Total".
        
        # We access by integer location (iloc) to be safe against name changes
        for index, row in ta_data.iterrows():
            new_row = table.add_row().cells
            
            # Safe fetch by index (iloc-like logic on row)
            def get_val(idx):
                if idx < len(row): return str(row.iloc[idx])
                return ""
            
            def get_num(idx):
                try:
                    val = str(row.iloc[idx]).replace('₹','').replace(',','')
                    return float(val)
                except:
                    return 0.0

            # 1-3 Departure (Indices 0,1,2)
            format_cell_text(new_row[0], get_val(0))
            format_cell_text(new_row[1], get_val(1))
            format_cell_text(new_row[2], get_val(2))

            # 4-6 Arrival (Indices 3,4,5)
            format_cell_text(new_row[3], get_val(3))
            format_cell_text(new_row[4], get_val(4))
            format_cell_text(new_row[5], get_val(5))

            # 7-8 Mode/Class (Indices 6,7)
            format_cell_text(new_row[6], get_val(6))
            format_cell_text(new_row[7], get_val(7))

            # 9 Ticket Rate (Index 8)
            format_cell_text(new_row[8], get_val(8))

            # 10 Fare Amount (A) (Index 9)
            fare_a = get_num(9)
            format_cell_text(new_row[9], f"{fare_a:.2f}")

            # 11-13 Road Amount (B) (Indices 10,11,12)
            km = get_num(10)
            rate = get_num(11)
            road_b = get_num(12)
            
            format_cell_text(new_row[10], f"{km:.1f}" if km else "-")
            format_cell_text(new_row[11], f"{rate:.1f}" if rate else "-")
            format_cell_text(new_row[12], f"{road_b:.2f}")

            # 14-18 DA Amount (C) (Indices 13,14,15)
            # Step 4 gives: 13:Days, 14:Rate, 15:DA_Amount
            da_days = get_num(13)
            da_rate = get_num(14)
            da_amt = get_num(15) 
            
            format_cell_text(new_row[13], f"{da_days}" if da_days else "")
            format_cell_text(new_row[14], f"{da_rate}" if da_rate else "")
            
            # Col 16 in Word is "Amount" (Gross). Col 17 is "Less". Col 18 is "Net DA".
            # Usually Step 4 calculates Net DA directly into Col 15 (DA Amount).
            # We will map DA Amount to Col 18 (Net DA) and put Gross in 16 if possible.
            # If we don't have "Less", we assume Gross = Net.
            
            format_cell_text(new_row[15], f"{da_amt:.2f}" if da_amt else "") # Gross
            format_cell_text(new_row[16], "") # Less (Placeholder)
            format_cell_text(new_row[17], f"{da_amt:.2f}" if da_amt else "") # Net DA (C)

            # 19 Grand Total (A + B + C)
            # Recalculate to be safe: Fare(9) + Road(12) + DA(15)
            row_total = fare_a + road_b + da_amt
            format_cell_text(new_row[18], f"{row_total:.2f}", bold=True)

            total_claim += row_total
            
            for cell in new_row:
                set_cell_margins(cell, top=50, bottom=50)

    # --- TOTAL ROW ---
    tot_row = table.add_row().cells
    tot_row[0].merge(tot_row[9]) # Merge first 10 cells
    format_cell_text(tot_row[0], "કુલ સરવાળો (Grand Total)", bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
    format_cell_text(tot_row[18], f"₹ {total_claim:.2f}", bold=True)

    return doc

# --- MAIN UI ---
st.info("Generating Final Report from Step 4 Data.")

if st.button("📄 Generate & Download Final A2 File"):
    if not df_ta.empty:
        try:
            doc = create_gujarati_doc(df_ta)
            
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
